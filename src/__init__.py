"""Racing AI Agent package powered by OpenAI and live iRacing telemetry."""

from .ai_agent import RacingAIAgent
from .mcp_client import RacingMCPClient

__version__ = "0.1.0"
__all__ = ["RacingAIAgent", "RacingMCPClient"]
