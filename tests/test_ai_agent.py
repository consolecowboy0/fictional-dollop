"""
Unit tests for the Racing AI Agent
"""

import pytest
from src.ai_agent import RacingAIAgent


class TestRacingAIAgent:
    """Test cases for RacingAIAgent"""
    
    def test_initialization_error_no_api_key(self, monkeypatch):
        """Test that initialization fails without API key"""
        # Remove API key from environment
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            RacingAIAgent()
    
    def test_initialization_with_api_key(self, monkeypatch):
        """Test initialization with API key"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
        
        agent = RacingAIAgent(model="gpt-3.5-turbo")
        assert agent.model == "gpt-3.5-turbo"
        assert agent.mcp_client is not None
        assert len(agent.conversation_history) == 0
    
    def test_initialization_with_custom_model(self, monkeypatch):
        """Test initialization with custom model"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
        
        agent = RacingAIAgent(model="gpt-4-turbo")
        assert agent.model == "gpt-4-turbo"
    
    def test_clear_conversation_history(self, monkeypatch):
        """Test clearing conversation history"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
        
        agent = RacingAIAgent()
        agent.conversation_history = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "response"}
        ]
        
        agent.clear_conversation_history()
        assert len(agent.conversation_history) == 0
    
    def test_format_racing_info(self, monkeypatch):
        """Test formatting of racing information"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
        
        agent = RacingAIAgent()
        racing_info = {
            "situation": {
                "position": "1st",
                "lap": "5/10"
            },
            "telemetry": {
                "rpm": 7500,
                "gear": 4
            },
            "track": {
                "name": "Silverstone",
                "weather": "Sunny"
            }
        }
        
        formatted = agent._format_racing_info(racing_info)
        
        assert "Race Situation:" in formatted
        assert "position: 1st" in formatted
        assert "Telemetry:" in formatted
        assert "rpm: 7500" in formatted
        assert "Track Information:" in formatted
        assert "name: Silverstone" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
