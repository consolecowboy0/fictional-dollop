"""
Unit tests for the Racing MCP Client
"""

import asyncio
import pytest
from src.mcp_client import RacingMCPClient


class TestRacingMCPClient:
    """Test cases for RacingMCPClient"""
    
    def test_initialization_default(self):
        """Test client initialization with default parameters"""
        client = RacingMCPClient()
        assert client.server_url == "http://localhost:3000"
        assert client.timeout == 30
        assert client.session is None
    
    def test_initialization_custom(self):
        """Test client initialization with custom parameters"""
        client = RacingMCPClient(
            server_url="http://example.com:8080",
            timeout=60
        )
        assert client.server_url == "http://example.com:8080"
        assert client.timeout == 60
        assert client.session is None
    
    @pytest.mark.asyncio
    async def test_get_racing_situation(self):
        """Test getting racing situation returns expected structure"""
        client = RacingMCPClient()
        situation = await client.get_racing_situation()
        
        assert isinstance(situation, dict)
        assert "position" in situation
        assert "lap" in situation
        assert "speed" in situation
        assert "track_conditions" in situation
        assert "vehicle_status" in situation
        assert "competitors" in situation
    
    @pytest.mark.asyncio
    async def test_get_telemetry(self):
        """Test getting telemetry returns expected structure"""
        client = RacingMCPClient()
        telemetry = await client.get_telemetry()
        
        assert isinstance(telemetry, dict)
        assert "rpm" in telemetry
        assert "gear" in telemetry
        assert "throttle" in telemetry
        assert "brake" in telemetry
        assert "steering" in telemetry
        assert "temperatures" in telemetry
    
    @pytest.mark.asyncio
    async def test_get_track_info(self):
        """Test getting track info returns expected structure"""
        client = RacingMCPClient()
        track_info = await client.get_track_info()
        
        assert isinstance(track_info, dict)
        assert "name" in track_info
        assert "length" in track_info
        assert "layout" in track_info
        assert "surface" in track_info
        assert "weather" in track_info
    
    @pytest.mark.asyncio
    async def test_list_available_tools_no_session(self):
        """Test listing tools without active session"""
        client = RacingMCPClient()
        tools = await client.list_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
