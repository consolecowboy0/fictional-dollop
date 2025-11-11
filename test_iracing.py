#!/usr/bin/env python3
"""
Simple test to check if we can grab iRacing data

This script tests basic iRacing data access without the full MCP setup.
"""

import asyncio


async def test_iracing_connection():
    """Test basic iRacing data retrieval"""
    print("=" * 70)
    print("IRACING DATA TEST")
    print("=" * 70)
    print()
    
    # First, let's check if iRacing SDK is available
    try:
        import irsdk
        print("✓ iRacing SDK (irsdk) is installed")
        
        # Try to connect to iRacing
        ir = irsdk.IRSDK()
        print("✓ iRacing SDK instance created")
        print()
        
        print("Attempting to connect to iRacing...")
        if ir.startup():
            print("✓ Connected to iRacing!")
            print()
            
            # Get some basic data
            print("Fetching iRacing data...")
            print("-" * 70)
            
            # Speed
            speed = ir['Speed']
            print(f"Speed: {speed} m/s" if speed else "Speed: Not available")
            
            # RPM
            rpm = ir['RPM']
            print(f"RPM: {rpm}" if rpm else "RPM: Not available")
            
            # Gear
            gear = ir['Gear']
            print(f"Gear: {gear}" if gear else "Gear: Not available")
            
            # Lap
            lap = ir['Lap']
            print(f"Lap: {lap}" if lap else "Lap: Not available")
            
            # Position
            position = ir['CarIdxLapDistPct']
            print(f"Position data available: {position is not None}")
            
            print("-" * 70)
            print()
            print("✓ Successfully retrieved iRacing data!")
            
            ir.shutdown()
        else:
            print("✗ Could not connect to iRacing")
            print()
            print("Possible reasons:")
            print("  1. iRacing is not running")
            print("  2. You're not in a session (practice, race, etc.)")
            print("  3. iRacing SDK access is disabled")
            print()
            print("To test:")
            print("  - Launch iRacing")
            print("  - Start a test session or race")
            print("  - Run this script again")
            
    except ImportError:
        print("✗ iRacing SDK (irsdk) is NOT installed")
        print()
        print("To install, run:")
        print("  pip install pyirsdk")
        print()
        print("This package allows Python to read data from iRacing.")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
        print("An unexpected error occurred while testing iRacing connection.")


if __name__ == "__main__":
    asyncio.run(test_iracing_connection())
