#!/usr/bin/env python3
"""
OpenAI Realtime API client for iRacing voice coaching.
Uses WebSocket connection for bi-directional audio streaming.
"""

import os
import json
import base64
import asyncio
import sounddevice as sd
import numpy as np
import queue
from websockets.asyncio.client import connect
from dotenv import load_dotenv
from src.mcp_client import RacingMCPClient

load_dotenv()


class RealtimeAPIClient:
    """OpenAI Realtime API client with audio I/O."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws = None
        self.racing_client = RacingMCPClient()
        
        # Audio settings (24kHz 16-bit mono PCM)
        self.sample_rate = 24000
        self.channels = 1
        self.chunk_size = 4096
        
        # Queues for audio
        self.input_queue = queue.Queue()
        self.speaker_stream = None
        
    async def connect(self):
        """Connect to OpenAI Realtime API via WebSocket."""
        url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        print("Connecting to OpenAI Realtime API...")
        self.ws = await connect(url, additional_headers=headers)
        print("✓ Connected to Realtime API")
        
        # Connect to iRacing
        print("\nConnecting to iRacing...")
        if self.racing_client.connect():
            print("✓ Connected to iRacing")
            track = self.racing_client.get_track_info()
            print(f"📍 Track: {track.get('name', 'Unknown')}\n")
        else:
            print("⚠️  Not connected to iRacing\n")
        
    async def configure_session(self):
        """Configure the session with instructions and voice."""
        # Get current racing context
        situation = self.racing_client.get_racing_situation()
        telemetry = self.racing_client.get_telemetry()
        track = self.racing_client.get_track_info()
        
        instructions = f"""You are an energetic racing coach providing real-time advice during an iRacing session.

Current session:
- Track: {track.get('name', 'Unknown')}
- Position: {situation.get('position', 'Unknown')}
- Speed: {telemetry.get('speed_mph', 0):.1f} mph

You have access to live telemetry through function calls. When asked about racing data, call the appropriate function.

Keep responses very brief (1-2 sentences), energetic, and actionable. You're coaching during an active race."""

        # Define available functions
        tools = [
            {
                "type": "function",
                "name": "get_telemetry",
                "description": "Get current vehicle telemetry including speed, RPM, gear, throttle, brake, fuel, and temperatures",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "get_racing_situation",
                "description": "Get current race position, lap number, track name, and nearby competitors",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "get_track_info",
                "description": "Get track conditions including weather, track temperature, and air temperature",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
        
        # Send session update
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": instructions,
                "voice": "echo",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.3,
                    "prefix_padding_ms": 200,
                    "silence_duration_ms": 400
                },
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.8,
                "max_response_output_tokens": 150
            }
        }
        
        await self.ws.send(json.dumps(config))
        print("✓ Session configured with racing coach personality\n")
        
    def audio_input_callback(self, indata, frames, time, status):
        """Callback for microphone input."""
        if status:
            print(f"Input status: {status}")
        # Put audio data in queue for processing
        self.input_queue.put(bytes(indata))
    
    async def send_audio(self):
        """Capture microphone audio and send to API."""
        print("🎤 Microphone active - speak naturally")
        
        # Open microphone stream
        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            blocksize=self.chunk_size,
            callback=self.audio_input_callback
        )
        
        try:
            with stream:
                while True:
                    # Get audio from queue
                    try:
                        data = self.input_queue.get(timeout=0.1)
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                        continue
                    
                    # Encode as base64
                    audio_b64 = base64.b64encode(data).decode('utf-8')
                    
                    # Send to API
                    message = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_b64
                    }
                    await self.ws.send(json.dumps(message))
                    
                    # Small delay to prevent overwhelming the API
                    await asyncio.sleep(0.01)
                
        except Exception as e:
            print(f"Microphone error: {e}")
                
    async def handle_messages(self):
        """Receive and handle messages from the API."""
        
        try:
            async for message in self.ws:
                event = json.loads(message)
                event_type = event.get("type")
                
                # Handle different event types
                if event_type == "session.created":
                    print(f"✓ Session created: {event.get('session', {}).get('id')}")
                    
                elif event_type == "session.updated":
                    print("✓ Session updated")
                    
                elif event_type == "conversation.item.created":
                    # New item in conversation
                    pass
                    
                elif event_type == "response.audio.delta":
                    # Audio chunk from assistant
                    audio_b64 = event.get("delta", "")
                    if audio_b64:
                        # Decode audio
                        audio_data = base64.b64decode(audio_b64)
                        
                        # Open speaker stream if not already open
                        if not self.speaker_stream:
                            self.speaker_stream = sd.RawOutputStream(
                                samplerate=self.sample_rate,
                                channels=self.channels,
                                dtype='int16'
                            )
                            self.speaker_stream.start()
                            print("🔊 Assistant speaking...")
                        
                        # Play audio directly
                        self.speaker_stream.write(audio_data)
                        
                elif event_type == "response.audio.done":
                    # Assistant finished speaking
                    if self.speaker_stream:
                        self.speaker_stream.stop()
                        self.speaker_stream.close()
                        self.speaker_stream = None
                    print("✓ Response complete\n")
                    
                elif event_type == "response.function_call_arguments.done":
                    # Function call from assistant
                    function_name = event.get("name")
                    call_id = event.get("call_id")
                    
                    print(f"📞 Calling function: {function_name}")
                    
                    # Call the MCP function
                    if function_name == "get_telemetry":
                        result = self.racing_client.get_telemetry()
                    elif function_name == "get_racing_situation":
                        result = self.racing_client.get_racing_situation()
                    elif function_name == "get_track_info":
                        result = self.racing_client.get_track_info()
                    else:
                        result = {"error": "Unknown function"}
                    
                    # Send result back to API
                    response = {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": json.dumps(result)
                        }
                    }
                    await self.ws.send(json.dumps(response))
                    
                    # Tell assistant to respond
                    await self.ws.send(json.dumps({"type": "response.create"}))
                    
                elif event_type == "error":
                    error_msg = event.get("error", {})
                    print(f"❌ Error: {error_msg}")
                    
                elif event_type == "input_audio_buffer.speech_started":
                    print("🎤 Listening...")
                    
                elif event_type == "input_audio_buffer.speech_stopped":
                    print("⏸️  Processing...")
                    
        except Exception as e:
            print(f"Message handling error: {e}")
        finally:
            if self.speaker_stream:
                self.speaker_stream.stop()
                self.speaker_stream.close()
                
    async def run(self):
        """Main run loop."""
        try:
            await self.connect()
            await self.configure_session()
            
            # Run audio sender and message handler concurrently
            await asyncio.gather(
                self.send_audio(),
                self.handle_messages()
            )
            
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            await self.cleanup()
            
    async def cleanup(self):
        """Clean up resources."""
        if self.ws:
            await self.ws.close()
        self.racing_client.disconnect()
        print("Disconnected")


async def main():
    """Entry point."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Set OPENAI_API_KEY in .env file")
        return
    
    print("=" * 60)
    print("iRacing Voice Coach - OpenAI Realtime API")
    print("=" * 60)
    print("\nPress Ctrl+C to quit\n")
    
    client = RealtimeAPIClient(api_key)
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())
