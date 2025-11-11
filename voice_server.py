#!/usr/bin/env python3
"""Simple Flask server to provide iRacing telemetry to browser voice chat."""

import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from src.mcp_client import RacingMCPClient

load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow browser to make requests

# Global racing client
racing_client = RacingMCPClient()
racing_client.connect()


@app.route('/api/telemetry')
def get_telemetry():
    """Get current telemetry data."""
    return jsonify({
        'situation': racing_client.get_racing_situation(),
        'telemetry': racing_client.get_telemetry(),
        'track': racing_client.get_track_info()
    })


@app.route('/api/session')
def create_session():
    """Create OpenAI Realtime session with racing context."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: No OPENAI_API_KEY found")
        return jsonify({'error': 'No API key configured'}), 500
    
    try:
        print("Creating ephemeral token for Realtime API...")
        
        # Create ephemeral token
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Get current telemetry for context
        telemetry = racing_client.get_telemetry()
        racing_info = racing_client.get_racing_situation()
        track = racing_client.get_track_info()
        
        print(f"Session telemetry - Track: {track.get('name')}, Position: {racing_info.get('position')}, Speed: {telemetry.get('speed_mph', 0):.1f} mph")
        
        instructions = f"""You are an energetic racing coach with real-time telemetry access.

CURRENT TELEMETRY:
- Track: {track.get('name', 'Unknown')}
- Position: {racing_info.get('position', 'Unknown')} 
- Lap: {racing_info.get('lap', 'Unknown')}
- Speed: {telemetry.get('speed_mph', 0):.1f} mph
- RPM: {telemetry.get('rpm', 0)}
- Gear: {telemetry.get('gear', 0)}

You will receive telemetry updates periodically via system messages. Always reference the MOST RECENT telemetry data when answering.

When the user asks about their position, speed, track, or any racing data, use the telemetry values above or from the most recent update.

Keep responses brief (1-2 sentences), actionable, and energetic. Act like a real racing coach."""
        
        payload = {
            "model": "gpt-4o-realtime-preview-2024-12-17",
            "voice": "echo",
            "instructions": instructions,
            "modalities": ["text", "audio"],
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.3,
                "prefix_padding_ms": 200,
                "silence_duration_ms": 400
            },
            "temperature": 0.8,
            "max_response_output_tokens": 150
        }
        
        response = requests.post(
            'https://api.openai.com/v1/realtime/sessions',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"OpenAI API error: {response.status_code}")
            print(f"Response: {response.text}")
            return jsonify({'error': f'OpenAI API error: {response.text}'}), response.status_code
        
        data = response.json()
        print(f"Session created successfully")
        print(f"Response keys: {data.keys()}")
        
        # Return the ephemeral token
        return jsonify({
            'client_secret': data
        })
        
    except Exception as e:
        print(f"ERROR creating session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("Starting voice chat server...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
