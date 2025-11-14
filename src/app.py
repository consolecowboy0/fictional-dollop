"""Flask application that exposes a simple web page for real-time
conversations with OpenAI's Realtime API using the Ash voice."""
from __future__ import annotations

import json
import os
import textwrap
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request

load_dotenv()

app = Flask(__name__)

DEFAULT_MODEL = "gpt-4o-realtime-preview-2024-12-17"
DEFAULT_INSTRUCTIONS = textwrap.dedent(
    """
    You are Ash. You are kind, quick to pick up on context, and speak in
    a clear, confident tone. You believe your name is Ash and you should
    introduce yourself as such when appropriate. Keep responses short and
    conversational, and guide the user if they seem unsure about what to
    try next.
    """
).strip()

INDEX_HTML = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Ash Realtime Chat</title>
    <style>
      :root {
        color-scheme: light dark;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI',
          sans-serif;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: radial-gradient(circle at top, #1e88e5 0%, #0d47a1 45%, #021f3f 100%);
        color: #f5f5f5;
      }
      .card {
        background: rgba(12, 23, 46, 0.85);
        border-radius: 18px;
        padding: 28px 32px;
        width: min(480px, 100% - 32px);
        box-shadow: 0 28px 60px rgba(2, 15, 42, 0.45);
        backdrop-filter: blur(12px);
      }
      h1 {
        margin-top: 0;
        font-size: 2.1rem;
        letter-spacing: 0.03em;
      }
      p.description {
        margin-top: 0.5rem;
        line-height: 1.55;
        opacity: 0.88;
      }
      button {
        appearance: none;
        border: none;
        border-radius: 999px;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: transform 160ms ease, box-shadow 160ms ease;
      }
      button.primary {
        background: linear-gradient(120deg, #4cafef, #2e73ff);
        color: #061223;
        box-shadow: 0 12px 24px rgba(18, 94, 209, 0.45);
      }
      button.primary:disabled {
        cursor: not-allowed;
        opacity: 0.65;
        transform: none;
        box-shadow: none;
      }
      button.primary:not(:disabled):hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 28px rgba(18, 94, 209, 0.5);
      }
      button.secondary {
        margin-left: 12px;
        background: rgba(255, 255, 255, 0.08);
        color: inherit;
      }
      .status {
        margin-top: 1.2rem;
        font-size: 0.95rem;
        opacity: 0.85;
      }
      .log {
        margin-top: 1.4rem;
        background: rgba(3, 12, 30, 0.68);
        border-radius: 12px;
        padding: 1rem;
        font-family: 'SFMono-Regular', Menlo, Consolas, monospace;
        max-height: 200px;
        overflow-y: auto;
        font-size: 0.85rem;
      }
      .log-entry {
        margin: 0.2rem 0;
      }
      .log-entry strong {
        font-weight: 600;
        margin-right: 0.35rem;
      }
      audio {
        display: none;
      }
    </style>
  </head>
  <body>
    <div class=\"card\">
      <h1>Talk with Ash</h1>
      <p class=\"description\">
        Press connect and start speaking. Your microphone audio is routed to
        OpenAI's realtime Ash voice. Ash will respond with streaming audio
        just like the ChatGPT mobile experience.
      </p>
      <div>
        <button id=\"connect\" class=\"primary\">Connect</button>
        <button id=\"disconnect\" class=\"secondary\" disabled>Disconnect</button>
      </div>
      <p class=\"status\" id=\"status\">Idle</p>
      <p class=\"status\" id=\"permission-hint\" hidden>
        Microphone permission is blocked. Use your browser's address bar or
        site settings to enable the microphone, then press connect again.
      </p>
      <div class=\"log\" id=\"log\"></div>
      <audio id=\"remote-audio\" autoplay playsinline></audio>
    </div>
    <script>
      const connectButton = document.getElementById('connect');
      const disconnectButton = document.getElementById('disconnect');
      const statusEl = document.getElementById('status');
      const permissionHintEl = document.getElementById('permission-hint');
      const logEl = document.getElementById('log');
      const remoteAudio = document.getElementById('remote-audio');

      let pc = null;
      let localStream = null;
      let dataChannel = null;

      function logMessage(source, message) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        const strong = document.createElement('strong');
        strong.textContent = source + ':';
        entry.appendChild(strong);
        entry.appendChild(document.createTextNode(message));
        logEl.appendChild(entry);
        logEl.scrollTop = logEl.scrollHeight;
      }

      function setStatus(text) {
        statusEl.textContent = text;
        logMessage('status', text);
      }

      function allowOnLocalhost() {
        const host = window.location.hostname;
        return host === 'localhost' || host === '127.0.0.1' || host === '[::1]';
      }

      function describePermissionError(error) {
        if (error && typeof error === 'object') {
          if (error.name === 'NotAllowedError' || error.name === 'SecurityError') {
            return (
              'Microphone permission was blocked. Use your browser\'s address bar or site settings to enable the microphone, then press connect again.'
            );
          }
          if (error.name === 'NotFoundError') {
            return 'No microphone was found. Plug one in or choose a different input device and try again.';
          }
        }
        return 'Unable to access the microphone.';
      }

      async function acquireMicrophoneStream() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error('Microphone access is not supported in this browser.');
        }

        if (!window.isSecureContext && !allowOnLocalhost()) {
          throw new Error(
            'Microphone capture requires HTTPS. Reopen this page using https:// or via http://localhost.'
          );
        }

        if (navigator.permissions?.query) {
          try {
            const status = await navigator.permissions.query({ name: 'microphone' });
            permissionHintEl.hidden = status.state !== 'denied';
          } catch (error) {
            logMessage('warn', `Unable to check microphone permission: ${error}`);
          }
        }

        return navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
          video: false,
        });
      }

      async function connect() {
        connectButton.disabled = true;
        setStatus('Requesting microphone access...');
        try {
          localStream = await acquireMicrophoneStream();
          permissionHintEl.hidden = true;
        } catch (error) {
          connectButton.disabled = false;
          const message = describePermissionError(error);
          setStatus(message);
          logMessage('error', String(error));
          if (navigator.permissions?.query) {
            try {
              const status = await navigator.permissions.query({ name: 'microphone' });
              permissionHintEl.hidden = status.state !== 'denied';
            } catch (permissionError) {
              logMessage('warn', `Unable to refresh permission status: ${permissionError}`);
            }
          }
          return;
        }

        setStatus('Creating session...');
        let sessionResponse;
        try {
          const resp = await fetch('/session', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
          if (!resp.ok) {
            const text = await resp.text();
            throw new Error(`Session failed: ${resp.status} ${text}`);
          }
          sessionResponse = await resp.json();
        } catch (error) {
          connectButton.disabled = false;
          setStatus('Unable to create session.');
          logMessage('error', String(error));
          return;
        }

        const clientSecret = sessionResponse?.client_secret?.value;
        const model = sessionResponse?.model;
        if (!clientSecret || !model) {
          connectButton.disabled = false;
          setStatus('Session response was missing credentials.');
          logMessage('error', JSON.stringify(sessionResponse));
          return;
        }

        pc = new RTCPeerConnection();
        pc.ontrack = (event) => {
          const [remoteStream] = event.streams;
          remoteAudio.srcObject = remoteStream;
          remoteAudio.play().catch((err) => logMessage('warn', `Autoplay prevented: ${err}`));
        };
        pc.onconnectionstatechange = () => {
          setStatus(`Connection state: ${pc.connectionState}`);
          if (pc.connectionState === 'failed' || pc.connectionState === 'closed' || pc.connectionState === 'disconnected') {
            disconnect();
          }
        };

        localStream.getTracks().forEach((track) => pc.addTrack(track, localStream));

        dataChannel = pc.createDataChannel('oai-events');
        dataChannel.onmessage = (event) => {
          logMessage('ash', event.data);
        };

        setStatus('Creating offer...');
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        setStatus('Sending offer to OpenAI...');
        const sdpResponse = await fetch(`https://api.openai.com/v1/realtime?model=${encodeURIComponent(model)}`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${clientSecret}`,
            'Content-Type': 'application/sdp',
            'OpenAI-Beta': 'realtime=v1'
          },
          body: offer.sdp
        });

        if (!sdpResponse.ok) {
          const text = await sdpResponse.text();
          throw new Error(`Realtime API error: ${sdpResponse.status} ${text}`);
        }

        const answer = {
          type: 'answer',
          sdp: await sdpResponse.text()
        };

        await pc.setRemoteDescription(answer);
        setStatus('Connected. Start talking to Ash!');
        disconnectButton.disabled = false;
        logMessage('ash', 'Connected and ready.');
      }

      function cleanupStreams() {
        if (localStream) {
          localStream.getTracks().forEach((track) => track.stop());
          localStream = null;
        }
        remoteAudio.srcObject = null;
      }

      function disconnect() {
        if (pc) {
          try {
            pc.close();
          } catch (error) {
            logMessage('warn', `Error while closing connection: ${error}`);
          }
        }
        pc = null;
        dataChannel = null;
        cleanupStreams();
        connectButton.disabled = false;
        disconnectButton.disabled = true;
        setStatus('Disconnected.');
      }

      connectButton.addEventListener('click', () => {
        if (pc) {
          setStatus('Already connected.');
          return;
        }
        connect().catch((error) => {
          setStatus('Error during connection.');
          logMessage('error', String(error));
          disconnect();
        });
      });

      disconnectButton.addEventListener('click', () => {
        disconnect();
      });

      window.addEventListener('beforeunload', () => {
        disconnect();
      });
    </script>
  </body>
</html>
"""


@app.get("/")
def index() -> Response:
    """Serve the single-page application."""
    return Response(INDEX_HTML, mimetype="text/html")


@app.post("/session")
def create_session() -> Response:
    """Create an ephemeral realtime session with OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY is not set on the server."}), 500

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
            f"OpenAI realtime session request failed: {error.code} {error.reason} - {error_body}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Failed to reach OpenAI realtime endpoint: {error.reason}") from error


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
