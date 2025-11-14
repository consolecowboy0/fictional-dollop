"""Minimal always-listening Flask demo for OpenAI's Realtime API."""
from __future__ import annotations

import json
import os
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request

if __package__ in (None, ""):
  sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
  from src.mcp_client import RacingMCPClient  # type: ignore
else:
  from .mcp_client import RacingMCPClient

load_dotenv()

app = Flask(__name__)

DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-12-17"
DEFAULT_INSTRUCTIONS = textwrap.dedent(
  """
  You are Ash, a calm and confident race engineer. You are always listening
  to a live audio stream. As soon as the driver finishes a sentence or takes
  a short pause, respond immediately with concise guidance using the latest
  telemetry snapshot that arrives as a user message before each reply.
  Keep responses short, actionable, and encouraging.
  """
).strip()

INDEX_HTML = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Ash Live Engineer</title>
    <style>
      :root {
        color-scheme: dark;
        font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
        background: radial-gradient(circle at top, #132f53, #050e1a 65%);
        color: #f2f6ff;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
      }
      .card {
        width: min(480px, 100%);
        background: rgba(8, 13, 28, 0.92);
        border-radius: 22px;
        padding: 32px;
        box-shadow: 0 30px 70px rgba(3, 8, 20, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(16px);
      }
      h1 {
        margin: 0 0 0.4rem;
        font-size: 2.1rem;
      }
      p.subtitle {
        margin: 0 0 1.5rem;
        opacity: 0.85;
        line-height: 1.5;
      }
      button#mute {
        width: 100%;
        height: 120px;
        border: none;
        border-radius: 999px;
        font-size: 1.1rem;
        font-weight: 600;
        cursor: pointer;
        color: #061123;
        background: linear-gradient(120deg, #66d1ff, #3475ff);
        box-shadow: 0 18px 35px rgba(32, 107, 255, 0.45);
        transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.15s ease;
      }
      button#mute.offline {
        opacity: 0.55;
        cursor: wait;
        box-shadow: none;
        background: rgba(255, 255, 255, 0.18);
        color: inherit;
      }
      button#mute.muted {
        transform: translateY(2px);
        background: linear-gradient(120deg, #ffb347, #ff6b6b);
        box-shadow: 0 14px 30px rgba(255, 105, 97, 0.45);
        color: #2b0b00;
      }
        p.hint {
          margin: 0 0 1.2rem;
          font-size: 0.9rem;
          opacity: 0.75;
        }
      .status {
        margin-top: 1.4rem;
        font-size: 0.95rem;
        opacity: 0.9;
      }
      .log {
        margin-top: 1.4rem;
        background: rgba(255, 255, 255, 0.04);
        border-radius: 16px;
        padding: 1rem;
        font-family: 'SFMono-Regular', Menlo, Consolas, monospace;
        font-size: 0.85rem;
        max-height: 180px;
        overflow-y: auto;
      }
      .log-entry {
        margin: 0.35rem 0;
      }
      .log-entry strong {
        margin-right: 0.4rem;
      }
      audio {
        display: none;
      }
    </style>
  </head>
  <body>
    <div class=\"card\">
      <h1>Live Engineer</h1>
      <p class=\"subtitle\">Ash listens continuously and replies whenever you pause.</p>
        <p class="hint">Need privacy? Tap mute. Otherwise just talk naturally.</p>
      <button id="mute" class="offline" disabled>Connecting…</button>
      <div class=\"status\" id=\"status\">Idle</div>
      <div class=\"log\" id=\"log\"></div>
      <audio id=\"remote-audio\" autoplay playsinline></audio>
    </div>
    <script>
      const statusEl = document.getElementById('status');
      const logEl = document.getElementById('log');
      const muteButton = document.getElementById('mute');
      const remoteAudio = document.getElementById('remote-audio');
      const CONVERSATION_ID = 'default';
      const SILENCE_THRESHOLD = 0.006;
      const SILENCE_MS = 500;
      const MIN_SPEECH_MS = 350;

      let pc = null;
      let dataChannel = null;
      let micStream = null;
      let micTrack = null;
      let ready = false;
      let isMuted = false;
      let audioContext = null;
      let analyser = null;
      let vadAnimationFrame = null;
      let vadLoop = null;
      let speechActive = false;
      let lastSpeechTimestamp = 0;
      let speechStartTimestamp = 0;
      let pendingResponse = false;

      function logMessage(source, message) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        entry.innerHTML = `<strong>${source}:</strong>${message}`;
        logEl.appendChild(entry);
        logEl.scrollTop = logEl.scrollHeight;
      }

      function setStatus(text) {
        statusEl.textContent = text;
        logMessage('status', text);
      }

      function formatTelemetrySummary(snapshot) {
        if (!snapshot || typeof snapshot !== 'object') {
          return 'Telemetry snapshot unavailable.';
        }
        if (snapshot.error) {
          return `Telemetry snapshot failed: ${snapshot.error}`;
        }
        const parts = [];
        const telemetry = snapshot.telemetry || {};
        const situation = snapshot.racing_situation || {};
        const track = snapshot.track || {};
        if (telemetry.speed_kph !== undefined) {
          parts.push(`Speed ${telemetry.speed_kph?.toFixed?.(1) || telemetry.speed_kph} km/h`);
        }
        if (telemetry.rpm !== undefined) {
          parts.push(`RPM ${Math.round(telemetry.rpm)}`);
        }
        if (telemetry.gear !== undefined) {
          parts.push(`Gear ${telemetry.gear}`);
        }
        if (situation.position) {
          parts.push(`P${situation.position}`);
        }
        if (situation.lap) {
          parts.push(`Lap ${situation.lap}`);
        }
        if (track.name) {
          parts.push(track.name);
        }
        const summaryLine = parts.length ? parts.join(' · ') : 'Telemetry snapshot captured.';
        return `Telemetry snapshot: ${summaryLine}`;
      }

      async function sendTelemetrySnapshot() {
        try {
          const response = await fetch('/telemetry_snapshot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload?.error || 'Telemetry request failed.');
          }
          const textSummary = formatTelemetrySummary(payload);
          logMessage('system', textSummary);
          if (dataChannel && dataChannel.readyState === 'open') {
            dataChannel.send(
              JSON.stringify({
                type: 'conversation.item.create',
                conversation: CONVERSATION_ID,
                item: {
                  type: 'message',
                  role: 'user',
                  content: [{ type: 'input_text', text: textSummary }],
                },
              })
            );
          }
        } catch (error) {
          logMessage('error', `Telemetry snapshot failed: ${error}`);
        }
      }

      async function ensureConnection() {
        if (ready) {
          return;
        }
        setStatus('Requesting microphone...');
        try {
          micStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true } });
        } catch (error) {
          setStatus('Microphone permission denied.');
          logMessage('error', String(error));
          muteButton.textContent = 'Microphone unavailable';
          muteButton.disabled = true;
          return;
        }

        micTrack = micStream.getAudioTracks()[0];
        micTrack.enabled = true;
        setupVoiceActivityDetector();

        setStatus('Creating realtime session...');
        const resp = await fetch('/session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        if (!resp.ok) {
          setStatus('Failed to create session.');
          logMessage('error', await resp.text());
          muteButton.textContent = 'Session failed';
          muteButton.disabled = true;
          return;
        }
        const session = await resp.json();
        const clientSecret = session?.client_secret?.value;
        const model = session?.model;
        if (!clientSecret || !model) {
          setStatus('Invalid session response.');
          logMessage('error', JSON.stringify(session));
          muteButton.textContent = 'Session invalid';
          muteButton.disabled = true;
          return;
        }

        pc = new RTCPeerConnection();
        pc.ontrack = (event) => {
          const [remoteStream] = event.streams;
          remoteAudio.srcObject = remoteStream;
        };
        pc.onconnectionstatechange = () => {
          logMessage('system', `Connection state: ${pc.connectionState}`);
          if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
            setStatus('Connection lost. Reload to retry.');
            ready = false;
            muteButton.classList.add('offline');
            muteButton.disabled = true;
            if (vadAnimationFrame) {
              cancelAnimationFrame(vadAnimationFrame);
              vadAnimationFrame = null;
            }
            if (audioContext) {
              audioContext.close().catch(() => {});
              audioContext = null;
              analyser = null;
              vadLoop = null;
            }
          }
        };

        pc.addTrack(micTrack, micStream);

        dataChannel = pc.createDataChannel('oai-events');
        dataChannel.onopen = () => {
          logMessage('system', 'Realtime channel ready.');
          muteButton.textContent = 'Mute microphone';
          muteButton.classList.remove('offline');
          muteButton.disabled = false;
          ready = true;
        };
        dataChannel.onmessage = (event) => {
          logMessage('ash', event.data);
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        const sdpResponse = await fetch(`https://api.openai.com/v1/realtime?model=${encodeURIComponent(model)}` , {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${clientSecret}`,
            'Content-Type': 'application/sdp',
            'OpenAI-Beta': 'realtime=v1'
          },
          body: offer.sdp,
        });

        if (!sdpResponse.ok) {
          setStatus('Realtime API error.');
          logMessage('error', await sdpResponse.text());
          return;
        }

        const answer = {
          type: 'answer',
          sdp: await sdpResponse.text(),
        };
        await pc.setRemoteDescription(answer);
        setStatus('Ash is listening continuously. Pause to hear guidance.');
      }

      function setupVoiceActivityDetector() {
        if (!micStream) {
          return;
        }
        if (!audioContext) {
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
          const source = audioContext.createMediaStreamSource(micStream);
          analyser = audioContext.createAnalyser();
          analyser.fftSize = 2048;
          source.connect(analyser);
          vadLoop = null;
        }
        if (!analyser) {
          return;
        }
        if (!vadLoop) {
          const dataArray = new Float32Array(analyser.fftSize);
          vadLoop = (timestamp) => {
            analyser.getFloatTimeDomainData(dataArray);
            let total = 0;
            for (let i = 0; i < dataArray.length; i += 1) {
              const sample = dataArray[i];
              total += sample * sample;
            }
            const rms = Math.sqrt(total / dataArray.length);
            const now = timestamp || performance.now();

            if (rms > SILENCE_THRESHOLD) {
              if (!speechActive) {
                speechActive = true;
                setStatus('Ash is listening... keep talking.');
                speechStartTimestamp = now;
              }
              lastSpeechTimestamp = now;
            } else if (speechActive && lastSpeechTimestamp && now - lastSpeechTimestamp > SILENCE_MS) {
              speechActive = false;
              handleSpeechSegmentEnd();
            }

            vadAnimationFrame = requestAnimationFrame(vadLoop);
          };
        }
        if (!vadAnimationFrame) {
          vadAnimationFrame = requestAnimationFrame(vadLoop);
        }
      }

      async function handleSpeechSegmentEnd() {
        if (pendingResponse || isMuted) {
          return;
        }
        const duration = lastSpeechTimestamp && speechStartTimestamp
          ? lastSpeechTimestamp - speechStartTimestamp
          : 0;
        speechStartTimestamp = 0;
        lastSpeechTimestamp = 0;
        if (duration < MIN_SPEECH_MS) {
          return;
        }
        pendingResponse = true;
        setStatus('Preparing a response from Ash...');
        try {
          await sendTelemetrySnapshot();
          if (dataChannel && dataChannel.readyState === 'open') {
            dataChannel.send(
              JSON.stringify({
                type: 'response.create',
                response: {
                  conversation: CONVERSATION_ID,
                  modalities: ['audio', 'text'],
                  instructions: 'Answer the driver promptly using the latest telemetry snapshot.',
                },
              })
            );
          }
          setStatus('Waiting for you to speak again.');
        } catch (error) {
          logMessage('error', `Failed to complete response: ${error}`);
          setStatus('Ash hit an issue preparing a response.');
        } finally {
          pendingResponse = false;
        }
      }

      muteButton.addEventListener('click', () => {
        if (!micTrack) {
          return;
        }
        isMuted = !isMuted;
        micTrack.enabled = !isMuted;
        if (isMuted) {
          muteButton.textContent = 'Unmute microphone';
          muteButton.classList.add('muted');
          setStatus('Microphone muted. Tap to resume.');
          if (vadAnimationFrame) {
            cancelAnimationFrame(vadAnimationFrame);
            vadAnimationFrame = null;
          }
          speechActive = false;
          speechStartTimestamp = 0;
          lastSpeechTimestamp = 0;
        } else {
          muteButton.textContent = 'Mute microphone';
          muteButton.classList.remove('muted');
          setStatus('Ash is listening continuously.');
          setupVoiceActivityDetector();
        }
      });

      window.addEventListener('beforeunload', () => {
        if (micStream) {
          micStream.getTracks().forEach((track) => track.stop());
        }
        if (pc) {
          pc.close();
        }
        if (vadAnimationFrame) {
          cancelAnimationFrame(vadAnimationFrame);
        }
        if (audioContext) {
          audioContext.close().catch(() => {});
        }
      });

      ensureConnection().catch((error) => {
        logMessage('error', `Failed to initialize connection: ${error}`);
        setStatus('Unable to initialize realtime session.');
      });
    </script>
  </body>
</html>
"""


@app.get("/")
def index() -> Response:
    """Serve the always-listening UI."""
    return Response(INDEX_HTML, mimetype="text/html")


@app.post("/session")
def create_session() -> Response:
    """Create an ephemeral realtime session with OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY is not set."}), 500

    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "voice": "ash",
        "modalities": ["audio", "text"],
        "instructions": DEFAULT_INSTRUCTIONS,
    }

    custom_body: Optional[Dict[str, Any]] = request.get_json(silent=True)
    if isinstance(custom_body, dict):
        payload.update({k: v for k, v in custom_body.items() if v is not None})

    try:
        response_data = _call_realtime_sessions(api_key, payload)
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(response_data)


def _call_realtime_sessions(api_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    request_data = json.dumps(payload).encode("utf-8")
    request_obj = urllib.request.Request(
        "https://api.openai.com/v1/realtime/sessions",
        data=request_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1",
        },
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"Realtime session request failed: {error.code} {error.reason} - {error_body}"
        ) from error
    except urllib.error.URLError as error:  # pragma: no cover - network issues
        raise RuntimeError(f"Failed to reach OpenAI realtime endpoint: {error.reason}") from error


def _collect_telemetry_snapshot() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "telemetry": None,
        "racing_situation": None,
        "track": None,
        "error": None,
    }
    client = RacingMCPClient()
    try:
        connected = client.connect()
        if not connected:
            snapshot["error"] = "Unable to connect to iRacing session."
            return snapshot

        try:
            snapshot["telemetry"] = client.get_telemetry()
        except RuntimeError as error:
            snapshot["telemetry"] = None
            snapshot["error"] = str(error)

        try:
            snapshot["racing_situation"] = client.get_racing_situation()
        except RuntimeError as error:
            snapshot.setdefault("details", {})["racing_situation"] = str(error)

        try:
            snapshot["track"] = client.get_track_info()
        except RuntimeError as error:
            snapshot.setdefault("details", {})["track_info"] = str(error)

        return snapshot
    finally:
        client.disconnect()


@app.post("/telemetry_snapshot")
def telemetry_snapshot() -> Response:
    snapshot = _collect_telemetry_snapshot()
    status = 200 if snapshot.get("error") in (None, "") else 503
    return jsonify(snapshot), status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
