"""
Racing AI Agent Package

A custom AI agent that connects to racing MCP servers and provides
intelligent analysis of sim-racing and sim-rally data.
"""

from .ai_agent import RacingAIAgent
from .mcp_client import RacingMCPClient

__version__ = "0.1.0"
__all__ = ["RacingAIAgent", "RacingMCPClient"]
