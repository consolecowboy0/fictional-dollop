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

from .mcp_client import RacingMCPClient

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

    You have limited access to live iRacing telemetry via the local MCP
    service. Only request telemetry when the racer explicitly asks for it
    or when you reasonably need the data to answer a racing-related
    question. To request data send a JSON message on the data channel in
    the following form: {"type":"tool_request","tool":"get_racing_situation"}.
    Available tools: get_racing_situation, get_telemetry, get_track_info.
    You will receive a matching tool_response message containing the data
    which you can summarise back to the racer.
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
      <div class=\"status\" id=\"status\">Idle</div>
      <div class=\"log\" id=\"log\"></div>
      <audio id=\"remote-audio\" autoplay playsinline></audio>
    </div>
    <script>
      const connectButton = document.getElementById('connect');
      const disconnectButton = document.getElementById('disconnect');
      const statusEl = document.getElementById('status');
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

      async function connect() {
        connectButton.disabled = true;
        setStatus('Requesting microphone access...');
        try {
          localStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true } });
        } catch (error) {
          connectButton.disabled = false;
          setStatus('Microphone permission denied.');
          logMessage('error', String(error));
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
          let parsed = null;
          try {
            parsed = JSON.parse(event.data);
          } catch (error) {
            // Non-JSON message, just log it.
          }

          if (parsed && parsed.type === 'tool_request') {
            handleToolRequest(parsed).catch((error) => {
              logMessage('error', `tool request failed: ${error}`);
            });
            return;
          }

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

      async function handleToolRequest(message) {
        const tool = message.tool;
        if (!tool) {
          logMessage('warn', 'tool request missing tool field');
          return;
        }

        logMessage('ash', `requesting ${tool} data...`);

        let response;
        try {
          response = await fetch('/mcp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool, args: message.args || {} }),
          });
        } catch (error) {
          logMessage('error', `failed to contact MCP endpoint: ${error}`);
          return;
        }

        if (!response.ok) {
          const text = await response.text();
          logMessage('error', `MCP error: ${response.status} ${text}`);
          return;
        }

        const payload = await response.json();
        logMessage('system', `MCP ${tool} data received.`);

        if (dataChannel && dataChannel.readyState === 'open') {
          dataChannel.send(
            JSON.stringify({ type: 'tool_response', tool, data: payload.data, error: payload.error || null })
          );
        }
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


def _call_mcp_tool(tool_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    client = RacingMCPClient()
    try:
        connected = client.connect()
        if not connected:
            return {"data": None, "error": "Unable to connect to iRacing session."}

        tool = getattr(client, tool_name, None)
        if not callable(tool):
            return {"data": None, "error": f"Unsupported tool '{tool_name}'."}

        if args and not isinstance(args, dict):
            return {"data": None, "error": "Tool arguments must be a JSON object."}

        if args:
            return {"data": None, "error": "This tool does not accept arguments."}

        data = tool()
        return {"data": data, "error": None}
    except RuntimeError as error:
        return {"data": None, "error": str(error)}
    finally:
        client.disconnect()


@app.post("/mcp")
def invoke_mcp_tool() -> Response:
    """Invoke a telemetry tool on the Racing MCP client."""

    request_body = request.get_json(silent=True) or {}
    tool_name = request_body.get("tool")
    if not tool_name:
        return jsonify({"error": "Missing 'tool' field."}), 400

    args = request_body.get("args")
    result = _call_mcp_tool(str(tool_name), args if isinstance(args, dict) else None)

    status = 200 if result["error"] in (None, "") else 503
    return jsonify(result), status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
