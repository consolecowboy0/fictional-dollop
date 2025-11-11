"""Simple synchronous telemetry client built directly on pyirsdk."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    import irsdk  # type: ignore
except ImportError:  # pragma: no cover - optional dependency for tests
    irsdk = None


class RacingMCPClient:
    """Minimal synchronous wrapper around irsdk.IRSDK."""

    def __init__(self, server_url: Optional[str] = None, timeout: int = 30, *_: Any, **__: Any) -> None:
        self.server_url = server_url or os.getenv("MCP_SERVER_URL", "http://localhost:3000")
        self.timeout = timeout
        self.session = None
        self._irsdk: Optional[Any] = None

    def connect(self) -> bool:
        """Initialize the IRSDK handle and attach to the sim."""
        if irsdk is None:
            raise RuntimeError("pyirsdk is required. Install it with `pip install pyirsdk`.")

        self._irsdk = irsdk.IRSDK()
        try:
            return self._irsdk.startup()
        except Exception:
            return False

    def disconnect(self) -> None:
        """Shutdown the IRSDK handle."""
        if not self._irsdk:
            return
        try:
            self._irsdk.shutdown()
        except Exception:
            pass
        self._irsdk = None

    def _ready(self) -> bool:
        """Check if IRSDK is connected."""
        return self._irsdk is not None and self._irsdk.is_connected

    def _get(self, name: str, default: Any = None) -> Any:
        """Helper to read a single iRacing variable safely."""
        if not self._ready():
            return default
        try:
            value = self._irsdk[name]
            return default if value is None else value
        except Exception:
            return default

    def get_racing_situation(self) -> Dict[str, Any]:
        """Return current race position, lap, speed, conditions, and competitors."""
        if not self._ready():
            return {
                "position": None,
                "lap": None,
                "speed": None,
                "track_conditions": {},
                "vehicle_status": {},
                "competitors": [],
            }

        speed_ms = self._get("Speed", 0.0)
        
        # Get session info for competitors
        session_info = self._irsdk.session_info_update or {}
        driver_info = session_info.get("DriverInfo", {}) if isinstance(session_info, dict) else {}
        drivers = driver_info.get("Drivers", []) if isinstance(driver_info, dict) else []
        
        # Get current camera car index
        cam_idx = self._get("CamCarIdx", -1)
        
        # Get player's position from the position array
        positions = self._get("CarIdxPosition", []) or []
        player_position = positions[cam_idx] if 0 <= cam_idx < len(positions) else None
        
        # Build competitors list
        competitors: List[Dict[str, Any]] = []
        positions = self._get("CarIdxPosition", []) or []
        for driver in drivers:
            if not isinstance(driver, dict):
                continue
            idx = driver.get("CarIdx", -1)
            if idx == cam_idx or idx < 0:
                continue
            pos = positions[idx] if 0 <= idx < len(positions) else None
            competitors.append({
                "name": driver.get("UserName", "Unknown"),
                "car": driver.get("CarScreenNameShort", "Unknown"),
                "car_number": driver.get("CarNumber", ""),
                "position": pos,
            })

        return {
            "position": player_position,
            "lap": self._get("Lap"),
            "lap_distance": self._get("LapDist"),
            "speed": {
                "m_s": speed_ms,
                "km_h": speed_ms * 3.6 if speed_ms else 0.0,
                "mph": speed_ms * 2.237 if speed_ms else 0.0,
            },
            "track_conditions": {
                "track_temp_c": self._get("TrackTempCrew"),
                "air_temp_c": self._get("AirTemp"),
                "weather_type": self._get("WeatherType"),
            },
            "vehicle_status": {
                "fuel_level_l": self._get("FuelLevel"),
                "fuel_percent": self._get("FuelLevelPct"),
                "oil_temp_c": self._get("OilTemp"),
                "water_temp_c": self._get("WaterTemp"),
            },
            "competitors": competitors,
        }

    def get_telemetry(self) -> Dict[str, Any]:
        """Return real-time telemetry: speed, RPM, gear, inputs, etc."""
        if not self._ready():
            return {
                "rpm": 0,
                "gear": 0,
                "throttle": 0.0,
                "brake": 0.0,
                "clutch": 0.0,
                "steering": 0.0,
                "speed_ms": 0.0,
                "speed_kph": 0.0,
                "speed_mph": 0.0,
                "temperatures": {},
            }

        speed_ms = float(self._get("Speed", 0.0))
        return {
            "rpm": self._get("RPM", 0),
            "gear": self._get("Gear", 0),
            "throttle": self._get("Throttle", 0.0),
            "brake": self._get("Brake", 0.0),
            "clutch": self._get("Clutch", 0.0),
            "steering": self._get("SteeringWheelAngle", 0.0),
            "speed_ms": speed_ms,
            "speed_kph": speed_ms * 3.6,
            "speed_mph": speed_ms * 2.237,
            "temperatures": {
                "oil_temp_c": self._get("OilTemp"),
                "water_temp_c": self._get("WaterTemp"),
            },
        }

    def get_track_info(self) -> Dict[str, Any]:
        """Return track name, length, layout, weather, etc."""
        if not self._ready():
            return {
                "name": "unknown",
                "length": "unknown",
                "layout": "unknown",
                "surface": "unknown",
                "weather": "unknown",
            }

        session_info = self._irsdk.session_info_update or {}
        weekend = session_info.get("WeekendInfo", {}) if isinstance(session_info, dict) else {}

        return {
            "name": weekend.get("TrackDisplayName", "unknown"),
            "length": weekend.get("TrackLength", "unknown"),
            "layout": weekend.get("TrackConfigName", "unknown"),
            "surface": weekend.get("TrackSurface", "unknown"),
            "weather": weekend.get("TrackWeatherType", "unknown"),
            "city": weekend.get("TrackCity"),
            "country": weekend.get("TrackCountry"),
        }

    def list_available_tools(self) -> List[str]:
        """Return list of available data methods."""
        return [
            "get_racing_situation",
            "get_telemetry",
            "get_track_info",
        ]
