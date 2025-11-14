"""Integration test for the synchronous RacingMCPClient."""

from pprint import pprint

from src.mcp_client import RacingMCPClient


def main() -> None:
    client = RacingMCPClient()
    connected = client.connect()
    print(f"Connected: {connected}")
    if not connected:
        return

    try:
        situation = client.get_racing_situation()
        telemetry = client.get_telemetry()
        track = client.get_track_info()

        print("\nRacing Situation:")
        pprint(situation)

        print("\nTelemetry:")
        pprint(telemetry)

        print("\nTrack Info:")
        pprint(track)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
