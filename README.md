# Racing AI Agent

A custom AI agent that uses OpenAI API to connect to a racing MCP (Model Context Protocol) server and gather information about sim-racing or sim-rally scenarios.

## Features

- 🏎️ **MCP Server Integration**: Connects to racing MCP servers for real-time simulator data
- 🤖 **AI-Powered Analysis**: Uses OpenAI GPT models to analyze racing situations
- 📊 **Comprehensive Data Gathering**: Retrieves telemetry, race position, track info, and more
- 🔌 **Extensible Design**: Built to easily extend functionality as the MCP server evolves
- 💬 **Interactive Mode**: Ask questions and get AI-powered racing insights

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

Create a `.env` file in the project root with the following variables:

```env
# Required: Your OpenAI API key
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional: MCP server configuration
MCP_SERVER_URL=http://localhost:3000
MCP_SERVER_TIMEOUT=30
```

### Getting an OpenAI API Key

1. Visit [OpenAI's website](https://platform.openai.com/)
2. Sign up or log in to your account
3. Navigate to API keys section
4. Create a new API key
5. Copy the key to your `.env` file

## Usage

### Basic Example

```python
import asyncio
from src import RacingAIAgent

async def main():
    # Initialize the agent
    agent = RacingAIAgent(model="gpt-4")
    
    # Connect to MCP server
    await agent.connect_to_server()
    
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
2. Connect to the MCP server
3. Demonstrate information gathering
4. Show AI analysis capabilities
5. Enter interactive Q&A mode

## Architecture

### Components

1. **RacingMCPClient** (`src/mcp_client.py`)
   - Handles connection to racing MCP servers
   - Provides methods to retrieve racing data:
     - `get_racing_situation()`: Current race position, lap, speed, etc.
     - `get_telemetry()`: RPM, gear, throttle, brake, steering, temps
     - `get_track_info()`: Track details and weather conditions
   - Designed for easy extension when actual MCP server is available

2. **RacingAIAgent** (`src/ai_agent.py`)
   - Integrates OpenAI for intelligent analysis
   - Maintains conversation context
   - Provides methods for:
     - Racing situation analysis
     - Question answering
     - Natural language insights

### Data Flow

```
Simulator → MCP Server → RacingMCPClient → RacingAIAgent → OpenAI → User
```

## Extending the Agent

The agent is designed to be easily extended once the MCP server is fully operational:

### Adding New Data Sources

```python
# In mcp_client.py, add new methods:
async def get_pit_strategy(self) -> Dict[str, Any]:
    """Get pit stop strategy recommendations."""
    # Implementation will query actual MCP server
    pass
```

### Custom Analysis Functions

```python
# In ai_agent.py, add specialized analysis:
def analyze_tire_wear(self, telemetry: Dict[str, Any]) -> str:
    """Analyze tire wear and recommend pit timing."""
    # Custom implementation
    pass
```

## Development Status

### Current Implementation

- ✅ Project structure and dependencies
- ✅ OpenAI integration with GPT models
- ✅ MCP client framework with placeholder methods
- ✅ AI agent with conversation context
- ✅ Example usage script with interactive mode
- ✅ Documentation and configuration examples

### Future Enhancements (when MCP server is ready)

- 🔄 Actual MCP server connection implementation
- 🔄 Real-time telemetry streaming
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

### MCP Server Connection

Currently, the MCP server connection is a placeholder. The message "HTTP connection not yet implemented" is expected until the actual racing MCP server is deployed.

## Contributing

Contributions are welcome! The agent is designed to grow with the MCP server implementation.

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
- Open an issue on GitHub
- Check existing documentation
- Review example.py for usage patterns
