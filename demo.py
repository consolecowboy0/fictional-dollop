#!/usr/bin/env python3
"""
Demo of the Racing AI Agent structure and MCP client

This demo shows the structure and capabilities without requiring an API key.
"""

from src.mcp_client import RacingMCPClient


def demo_mcp_client():
    """Demonstrate MCP client functionality"""
    print("=" * 70)
    print("RACING AI AGENT - MCP CLIENT DEMO")
    print("=" * 70)
    print()
    
    # Initialize client
    print("1. Initializing Racing MCP Client...")
    client = RacingMCPClient(server_url="http://localhost:3000")
    print("   ✓ Client initialized")
    print(f"   - Legacy Server URL setting: {client.server_url}")
    print(f"   - Timeout: {client.timeout}s")
    print()
    
    # Connect
    print("2. Connecting to live iRacing session...")
    try:
        connected = client.connect()
    except RuntimeError as exc:
        print(f"   ✗ Could not initialize pyirsdk: {exc}")
        connected = False
    else:
        if connected:
            print("   ✓ Connected to live telemetry stream")
        else:
            print("   ! iRacing not detected. Start a session to see live data.")
    print()
    
    # Get racing situation
    print("3. Gathering Racing Situation Data...")
    situation = client.get_racing_situation()
    print("   ✓ Racing situation retrieved:")
    for key, value in situation.items():
        print(f"      - {key}: {value}")
    print()
    
    # Get telemetry
    print("4. Gathering Telemetry Data...")
    telemetry = client.get_telemetry()
    print("   ✓ Telemetry retrieved:")
    for key, value in telemetry.items():
        print(f"      - {key}: {value}")
    print()
    
    # Get track info
    print("5. Gathering Track Information...")
    track = client.get_track_info()
    print("   ✓ Track information retrieved:")
    for key, value in track.items():
        print(f"      - {key}: {value}")
    print()
    
    # List tools
    print("6. Checking Available Telemetry Tools...")
    tools = client.list_available_tools()
    print(f"   ✓ Available tools: {len(tools)}")
    for tool in tools:
        print(f"      - {tool}")
    print()
    
    # Disconnect
    print("7. Disconnecting from iRacing...")
    client.disconnect()
    print("   ✓ Disconnected from pyirsdk")
    print()
    
    print("=" * 70)
    print("MCP CLIENT CAPABILITIES SUMMARY")
    print("=" * 70)
    print()
    print("✓ Generic information gathering methods:")
    print("  - get_racing_situation() - Current race position, lap, speed, etc.")
    print("  - get_telemetry()        - Vehicle telemetry (RPM, gear, inputs)")
    print("  - get_track_info()       - Track details and conditions")
    print("  - list_available_tools() - Discover exposed telemetry helpers")
    print()
    print("✓ Extensible design:")
    print("  - Easy to extend with more iRacing variables")
    print("  - Fall back to safe defaults when no session is active")
    print("  - Simple synchronous API for straightforward usage")
    print()
    print("✓ AI Agent Integration:")
    print("  - Works with RacingAIAgent to provide OpenAI-powered analysis")
    print("  - Maintains conversation context for natural interactions")
    print("  - Formats racing data for optimal AI understanding")
    print()
    
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("To use with actual racing data:")
    print()
    print("1. Install pyirsdk (pip install pyirsdk)")
    print("2. Launch iRacing and join a session")
    print("3. Run this demo to see live telemetry output")
    print("4. Add OpenAI API key to .env file for AI analysis")
    print("5. Run example.py for full AI-powered racing insights")
    print()
    print("For AI-powered analysis demonstration:")
    print("  - Set OPENAI_API_KEY in .env file")
    print("  - Run: python example.py")
    print()


def show_architecture():
    """Display the system architecture"""
    print()
    print("=" * 70)
    print("SYSTEM ARCHITECTURE")
    print("=" * 70)
    print()
    print("┌─────────────┐")
    print("│  Simulator  │  (iRacing, Assetto Corsa, etc.)")
    print("└──────┬──────┘")
    print("       │")
    print("       ▼")
    print("┌──────────────────┐")
    print("│ RacingMCPClient  │  ✓ Implemented")
    print("│  - pyirsdk link  │")
    print("│  - Live data     │")
    print("└──────┬───────────┘")
    print("       │")
    print("       ▼")
    print("┌──────────────────┐")
    print("│  RacingAIAgent   │  ✓ Implemented")
    print("│  - OpenAI API    │")
    print("│  - Analysis      │")
    print("│  - Conversations │")
    print("└──────┬───────────┘")
    print("       │")
    print("       ▼")
    print("┌─────────────┐")
    print("│    User     │  (Q&A, insights, coaching)")
    print("└─────────────┘")
    print()


def main():
    """Main demo function"""
    show_architecture()
    demo_mcp_client()
    
    print("=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
