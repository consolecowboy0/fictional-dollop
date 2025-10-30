#!/usr/bin/env python3
"""
Example usage of the Racing AI Agent

This script demonstrates how to use the Racing AI Agent to connect to
a racing MCP server and gather information about sim-racing or sim-rally.
"""

import asyncio
import sys
from src import RacingAIAgent


async def main():
    """Main example function."""
    print("=" * 60)
    print("Racing AI Agent - Example Usage")
    print("=" * 60)
    print()
    
    try:
        # Initialize the AI agent
        print("Initializing Racing AI Agent...")
        agent = RacingAIAgent(
            # API key will be loaded from .env file
            # Or you can pass it directly: openai_api_key="your-key-here"
            model="gpt-4"  # or "gpt-3.5-turbo" for faster/cheaper responses
        )
        print("✓ Agent initialized successfully")
        print()
        
        # Connect to the MCP server
        print("Connecting to racing MCP server...")
        await agent.connect_to_server()
        print("✓ Connected to MCP server")
        print("  (Note: This is a placeholder until the actual MCP server is available)")
        print()
        
        # Example 1: Get racing information
        print("-" * 60)
        print("Example 1: Gathering Racing Information")
        print("-" * 60)
        racing_info = await agent.get_racing_info()
        print("Racing Information:")
        print(f"  Situation: {racing_info['situation']}")
        print(f"  Telemetry: {racing_info['telemetry']}")
        print(f"  Track: {racing_info['track']}")
        print()
        
        # Example 2: Analyze racing situation
        print("-" * 60)
        print("Example 2: AI Analysis of Racing Situation")
        print("-" * 60)
        analysis = agent.analyze_racing_situation(racing_info)
        print("AI Analysis:")
        print(analysis)
        print()
        
        # Example 3: Ask specific questions
        print("-" * 60)
        print("Example 3: Ask Specific Questions")
        print("-" * 60)
        
        questions = [
            "What is the optimal racing line for this track?",
            "How can I improve my lap times?",
            "What are the best overtaking opportunities on this track?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\nQuestion {i}: {question}")
            answer = agent.ask_question(question, racing_info)
            print(f"Answer: {answer}")
        
        print()
        
        # Example 4: Interactive mode
        print("-" * 60)
        print("Example 4: Interactive Mode")
        print("-" * 60)
        print("You can now ask questions about racing.")
        print("Type 'quit' or 'exit' to end the session.")
        print()
        
        while True:
            try:
                user_input = input("Your question: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Exiting interactive mode...")
                    break
                
                if not user_input:
                    continue
                
                # Get fresh racing info (in real scenario, this would be live data)
                racing_info = await agent.get_racing_info()
                
                # Get AI response
                response = agent.ask_question(user_input, racing_info)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                print("\nInterrupted by user")
                break
        
        # Disconnect from server
        print()
        print("Disconnecting from MCP server...")
        await agent.disconnect_from_server()
        print("✓ Disconnected successfully")
        
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("\nPlease ensure you have:")
        print("1. Created a .env file based on .env.example")
        print("2. Set your OPENAI_API_KEY in the .env file")
        sys.exit(1)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
