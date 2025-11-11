#!/usr/bin/env python3
"""Simple chat interface with GPT that has access to live iRacing data."""

import os
from dotenv import load_dotenv
from openai import OpenAI
from src.mcp_client import RacingMCPClient

load_dotenv()


def main():
    # Setup
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: Set OPENAI_API_KEY in .env file")
        return
    
    openai = OpenAI(api_key=api_key)
    client = RacingMCPClient()
    
    # Connect to iRacing
    print("Connecting to iRacing...")
    if client.connect():
        print("✓ Connected\n")
    else:
        print("! Not connected - will return defaults\n")
    
    print("Chat with GPT (has access to your live race data)")
    print("Type 'quit' to exit\n")
    
    # Chat loop
    while True:
        question = input("You: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            break
        
        if not question:
            continue
        
        # Get live race data
        racing_situation = client.get_racing_situation()
        telemetry = client.get_telemetry()
        track = client.get_track_info()
        
        # Build prompt with race data
        prompt = f"""Current racing data:
Position: {racing_situation.get('position')}
Lap: {racing_situation.get('lap')}
Speed: {telemetry.get('speed_mph'):.1f} mph
RPM: {telemetry.get('rpm')}
Gear: {telemetry.get('gear')}
Throttle: {telemetry.get('throttle'):.0%}
Brake: {telemetry.get('brake'):.0%}
Track: {track.get('name')}

Question: {question}"""
        
        # Ask GPT
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a racing coach with access to live telemetry. Give concise, helpful advice."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            print(f"\nGPT: {response.choices[0].message.content}\n")
        
        except Exception as e:
            print(f"\nError: {e}\n")
    
    client.disconnect()
    print("Disconnected")


if __name__ == "__main__":
    main()
