# Racing AI Agent

A custom AI agent that combines OpenAI with live iRacing telemetry (via [pyirsdk](https://pypi.org/project/pyirsdk)) to gather and explain what is happening on track in real time.

## Features

- 🏎️ **Live iRacing Telemetry**: Streams car, track, and session data directly from iRacing using pyirsdk
- 🤖 **AI-Powered Analysis**: Uses OpenAI GPT models to turn telemetry into concise coaching insights
- 📊 **Comprehensive Data Gathering**: Pulls position, lap info, vehicle status, track conditions, and competitor context
- 🔌 **Extensible Design**: Easily add new telemetry fields or derived metrics within the async-friendly client
- 💬 **Interactive Mode**: Ask custom questions about the current session and get AI-powered responses

## Installation

1. Clone the repository:
```bash
git clone https://github.com/consolecowboy0/fictional-dollop.git
cd fictional-dollop
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Configuration

Create a `.env` file in the project root with the following variable:

```env
# Required: Your OpenAI API key
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### Getting an OpenAI API Key

1. Visit [OpenAI's website](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API keys section
4. Create a new API key
5. Copy the key to your `.env` file

## Usage

> **Note:** Launch iRacing and join a session before calling `connect_to_server()` to receive live telemetry. When no session is active the client returns safe default values so demos can still run.

### Basic Example

```python
import asyncio
from src import RacingAIAgent

async def main():
    # Initialize the agent
    agent = RacingAIAgent(model="gpt-4")
    
    # Connect to live iRacing telemetry (returns False if iRacing is not running)
    connected = await agent.connect_to_server()
    if not connected:
        print("iRacing session not found. Start a session and try again.")
        return
    
    # Get racing information
    racing_info = await agent.get_racing_info()
    
    # Analyze the situation
    analysis = agent.analyze_racing_situation(racing_info)
    print(analysis)
    
    # Ask specific questions
    response = agent.ask_question(
        "What's the best strategy for this race?",
        racing_info
    )
    print(response)
    
    # Disconnect
    await agent.disconnect_from_server()

asyncio.run(main())
```

### Running the Example Script

The repository includes a comprehensive example script:

```bash
python example.py
```

This will:
1. Initialize the AI agent
2. Attempt to connect to the live iRacing session
3. Demonstrate information gathering
4. Show AI analysis capabilities
5. Enter interactive Q&A mode

## Architecture

### Components

1. **RacingMCPClient** (`src/mcp_client.py`)
    - Wraps pyirsdk for live iRacing telemetry access
    - Provides methods to retrieve racing data:
     - `get_racing_situation()`: Current race position, lap, speed, etc.
     - `get_telemetry()`: RPM, gear, throttle, brake, steering, temps
     - `get_track_info()`: Track details and weather conditions
    - Designed for easy extension with additional telemetry variables

2. **RacingAIAgent** (`src/ai_agent.py`)
   - Integrates OpenAI for intelligent analysis
   - Maintains conversation context
   - Provides methods for:
     - Racing situation analysis
     - Question answering
     - Natural language insights

### Data Flow

```
iRacing Simulator → pyirsdk → RacingMCPClient → RacingAIAgent → OpenAI → User
```

## Extending the Agent

The agent is designed to be easily extended as you experiment with new telemetry-driven ideas:

### Adding New Data Sources

```python
# In mcp_client.py, add new methods:
async def get_pit_strategy(self) -> Dict[str, Any]:
    """Get pit stop strategy recommendations."""
    # Implementation could derive strategy from pyirsdk telemetry or custom logic
    ...
```

### Custom Analysis Functions

```python
# In ai_agent.py, add specialized analysis:
def analyze_tire_wear(self, telemetry: Dict[str, Any]) -> str:
    """Analyze tire wear and recommend pit timing."""
    # Inspect telemetry["temperatures"] and return actionable guidance
    ...
```

## Development Status

### Current Implementation

- ✅ Project structure and dependencies
- ✅ OpenAI integration with GPT models
- ✅ pyirsdk-powered telemetry client with safe fallbacks
- ✅ AI agent with conversation context
- ✅ Example usage script with interactive mode
- ✅ Documentation and configuration examples

### Future Enhancements

- 🔄 Additional derived metrics (sector deltas, stint analysis)
- 🔄 Historical telemetry capture and playback
- 🔄 Historical data analysis
- 🔄 Race strategy optimization
- 🔄 Setup recommendations
- 🔄 Performance comparison tools

## Troubleshooting

### API Key Issues

If you see "OpenAI API key is required" error:
1. Ensure `.env` file exists in the project root
2. Verify `OPENAI_API_KEY` is set correctly
3. Check there are no extra spaces or quotes around the key

### Telemetry Connection

- Ensure iRacing is running and you are loaded into a session before calling `connect_to_server()`.
- Confirm `pyirsdk` installed correctly (`pip show pyirsdk`).
- On Windows, run your shell as an administrator if you see access errors when attaching to iRacing.
- The helper methods fall back to default values when telemetry is unavailable, so seeing `None`/`unknown` means the client could not read live data.

## Contributing

Contributions are welcome! The agent is designed to grow alongside new telemetry sources and racing workflows.

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review example.py for usage patterns
