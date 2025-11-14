"""Flask application that exposes a simple web page for real-time
conversations with OpenAI's Realtime API using the Ash voice."""
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
    # Allow running `python src/app.py` by ensuring the repository root is on sys.path.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.mcp_client import RacingMCPClient  # type: ignore
else:
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

    The racer can push live iRacing telemetry snapshots directly into this
    conversation. These snapshots arrive as normal user messages that
    contain structured JSON data (for example: get_racing_situation,
    get_telemetry, get_track_info). When you see one, read the data and
    summarise it back to the racer in plain language, highlighting
    insights or potential next steps. Do not wait for any tool responses;
    everything you need will be embedded in the message you receive.
    """
).strip()

INDEX_HTML = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <style>
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
      .actions {
        margin-top: 1rem;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
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
      <div class=\"actions\">
        <button id=\"snapshot\" class=\"secondary\" disabled>Send MCP Snapshot</button>
      </div>
      <audio id=\"remote-audio\" autoplay playsinline></audio>
    </div>
    <script>
      const connectButton = document.getElementById('connect');
      const disconnectButton = document.getElementById('disconnect');
      const snapshotButton = document.getElementById('snapshot');
      const statusEl = document.getElementById('status');
      const logEl = document.getElementById('log');
      const remoteAudio = document.getElementById('remote-audio');
      const snapshotButtonLabel = snapshotButton.textContent;
      const CONVERSATION_ID = 'default';

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

      function resetSnapshotButton(disable = true) {
        if (disable) {
          snapshotButton.disabled = true;
        }
        snapshotButton.textContent = snapshotButtonLabel;
      }

      async function connect() {
        connectButton.disabled = true;
        resetSnapshotButton(true);
        setStatus('Requesting microphone access...');
        try {
          localStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true } });
        } catch (error) {
          connectButton.disabled = false;
          resetSnapshotButton(true);
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
          resetSnapshotButton(true);
          setStatus('Unable to create session.');
          logMessage('error', String(error));
          return;
        }

        const clientSecret = sessionResponse?.client_secret?.value;
        const model = sessionResponse?.model;
        if (!clientSecret || !model) {
          connectButton.disabled = false;
          resetSnapshotButton(true);
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
        snapshotButton.disabled = false;
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
        snapshotButton.disabled = true;
        snapshotButton.textContent = snapshotButtonLabel;
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

      function formatSnapshotText(snapshot) {
        if (!snapshot || typeof snapshot !== 'object') {
          return 'MCP snapshot is unavailable.';
        }
        if (snapshot.error) {
          return `MCP snapshot failed: ${snapshot.error}`;
        }
        const tools = snapshot.tools || {};
        const parts = Object.entries(tools).map(([name, entry]) => {
          if (!entry) {
            return `${name}: no data`;
          }
          if (entry.error) {
            return `${name}: error - ${entry.error}`;
          }
          try {
            return `${name}: ${JSON.stringify(entry.data)}`;
          } catch (error) {
            return `${name}: data available`;
          }
        });
        if (!parts.length) {
          return 'MCP snapshot returned no tools.';
        }
        return `MCP snapshot data\n${parts.join('\n')}`;
      }

      async function pushMcpSnapshotToChat() {
        if (!pc || pc.connectionState !== 'connected') {
          logMessage('warn', 'Connect to Ash before sending a snapshot.');
          return;
        }
        if (!dataChannel || dataChannel.readyState !== 'open') {
          logMessage('warn', 'Realtime data channel is not ready.');
          return;
        }

        snapshotButton.disabled = true;
        snapshotButton.textContent = 'Sending snapshot...';
        try {
          const response = await fetch('/mcp_snapshot', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
          const payload = await response.json();
          if (!response.ok) {
            const errorMessage = payload?.error || 'Snapshot request failed.';
            logMessage('error', errorMessage);
            return;
          }

          const textSummary = formatSnapshotText(payload);
          logMessage('system', textSummary);

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
          dataChannel.send(
            JSON.stringify({
              type: 'response.create',
              response: {
                conversation: CONVERSATION_ID,
                instructions: 'Use the latest MCP snapshot message to answer the racer.',
                modalities: ['audio', 'text'],
              },
            })
          );
        } catch (error) {
          logMessage('error', `Failed to send snapshot: ${error}`);
        } finally {
          snapshotButton.disabled = false;
          snapshotButton.textContent = snapshotButtonLabel;
        }
      }

      snapshotButton.addEventListener('click', () => {
        pushMcpSnapshotToChat().catch((error) => {
          logMessage('error', String(error));
        });
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


def _collect_all_tool_data() -> Dict[str, Any]:
    client = RacingMCPClient()
    snapshot: Dict[str, Any] = {"tools": {}, "error": None}
    try:
        connected = client.connect()
        if not connected:
            snapshot["error"] = "Unable to connect to iRacing session."
            return snapshot

        available_tools = []
        try:
            available_tools = client.list_available_tools()
        except Exception as error:  # pragma: no cover - defensive guard
            snapshot["error"] = f"Failed to list tools: {error}"
            return snapshot

        for tool_name in available_tools:
            tool = getattr(client, tool_name, None)
            if not callable(tool):
                snapshot["tools"][tool_name] = {"data": None, "error": "Tool not callable."}
                continue
            try:
                data = tool()
                snapshot["tools"][tool_name] = {"data": data, "error": None}
            except RuntimeError as error:
                snapshot["tools"][tool_name] = {"data": None, "error": str(error)}
            except Exception as error:  # pragma: no cover - unexpected failure
                snapshot["tools"][tool_name] = {"data": None, "error": f"Unexpected error: {error}"}

        return snapshot
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
    tool_request_id = request_body.get("tool_request_id")
    tool_call_id = request_body.get("tool_call_id")
    result = _call_mcp_tool(str(tool_name), args if isinstance(args, dict) else None)
    result["tool_request_id"] = tool_request_id
    result["tool_call_id"] = tool_call_id

    status = 200 if result["error"] in (None, "") else 503
    return jsonify(result), status


@app.post("/mcp_snapshot")
def mcp_snapshot() -> Response:
    """Return a dump of all available MCP tool data."""

    snapshot = _collect_all_tool_data()
    status = 200 if snapshot.get("error") in (None, "") else 503
    return jsonify(snapshot), status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
