"""AI agent that combines OpenAI with live iRacing telemetry via pyirsdk."""

import os
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

from .mcp_client import RacingMCPClient


class RacingAIAgent:
    """
    AI Agent for sim-racing and sim-rally information gathering and analysis.
    
    This agent connects to live iRacing telemetry (through RacingMCPClient)
    and uses OpenAI to interpret the data, providing natural language
    insights about the current racing situation.
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4",
        mcp_server_url: Optional[str] = None
    ):
        """
        Initialize the Racing AI Agent.
        
        Args:
            openai_api_key: OpenAI API key (optional, defaults to env var)
            model: OpenAI model to use (default: gpt-4)
            mcp_server_url: URL of the MCP server (optional, defaults to env var)
        """
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        
    # Initialize MCP client
        self.mcp_client = RacingMCPClient(server_url=mcp_server_url)
        
        # Conversation history for context
        self.conversation_history: List[Dict[str, str]] = []
        
    def connect_to_server(self) -> bool:
        """Connect to the live iRacing telemetry stream.

        Returns:
            True if the connection succeeded, False otherwise.
        """

        return self.mcp_client.connect()
    
    def disconnect_from_server(self):
        """Disconnect from the underlying telemetry provider."""
        self.mcp_client.disconnect()
    
    def get_racing_info(self) -> Dict[str, Any]:
        """
        Gather comprehensive racing information from the MCP server.
        
        Returns:
            Dictionary containing all available racing information
        """
        racing_situation = self.mcp_client.get_racing_situation()
        telemetry = self.mcp_client.get_telemetry()
        track_info = self.mcp_client.get_track_info()
        
        return {
            "situation": racing_situation,
            "telemetry": telemetry,
            "track": track_info
        }
    
    def analyze_racing_situation(self, racing_info: Dict[str, Any], query: Optional[str] = None) -> str:
        """
        Use OpenAI to analyze the racing situation and provide insights.
        
        Args:
            racing_info: Racing information dictionary
            query: Optional specific query about the racing situation
            
        Returns:
            AI-generated analysis or response to query
        """
        # Build the system prompt
        system_prompt = """You are an expert racing analyst and coach for sim-racing and sim-rally.
        You have access to real-time telemetry and racing information from a simulator.
        Provide clear, actionable insights and advice based on the data provided.
        Be concise but informative."""
        
        # Build the user prompt
        if query:
            user_prompt = f"""Current racing situation:
{self._format_racing_info(racing_info)}

Query: {query}

Please provide a detailed response to the query based on the racing data."""
        else:
            user_prompt = f"""Current racing situation:
{self._format_racing_info(racing_info)}

Please provide an analysis of the current racing situation including:
1. Overall position and performance
2. Vehicle status and any concerns
3. Recommendations for improvement"""
        
        # Add to conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Include recent conversation history for context
        messages.extend(self.conversation_history[-5:])  # Keep last 5 exchanges
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            assistant_message = response.choices[0].message.content
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_prompt})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            return f"Error analyzing racing situation: {str(e)}"
    
    def ask_question(self, question: str, racing_info: Optional[Dict[str, Any]] = None) -> str:
        """
        Ask a specific question about the racing situation.
        
        Args:
            question: Question to ask
            racing_info: Optional racing information (if None, will be fetched)
            
        Returns:
            AI-generated answer
        """
        if racing_info is None:
            # If no racing info provided, use placeholder
            racing_info = {
                "situation": {"note": "No live data available"},
                "telemetry": {},
                "track": {}
            }
        
        return self.analyze_racing_situation(racing_info, query=question)
    
    def clear_conversation_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
    
    def _format_racing_info(self, racing_info: Dict[str, Any]) -> str:
        """
        Format racing information for the AI prompt.
        
        Args:
            racing_info: Racing information dictionary
            
        Returns:
            Formatted string representation
        """
        lines = []
        
        # Format situation
        if "situation" in racing_info:
            lines.append("Race Situation:")
            for key, value in racing_info["situation"].items():
                lines.append(f"  - {key}: {value}")
        
        # Format telemetry
        if "telemetry" in racing_info:
            lines.append("\nTelemetry:")
            for key, value in racing_info["telemetry"].items():
                lines.append(f"  - {key}: {value}")
        
        # Format track info
        if "track" in racing_info:
            lines.append("\nTrack Information:")
            for key, value in racing_info["track"].items():
                lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines)
