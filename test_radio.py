"""Test if winsdk Radio API works on this system."""
import asyncio

async def test_radios():
    try:
        from winsdk.windows.devices.radios import Radio, RadioState, RadioKind
        print("[OK] winsdk imported successfully")
        
        radios = await Radio.get_radios_async()
        print(f"[OK] Found {len(radios)} radios:")
        
        for radio in radios:
            kind_name = {0: "Other", 1: "WiFi", 2: "MobileBroadband", 3: "Bluetooth", 4: "FM"}.get(radio.kind, "Unknown")
            state_name = {0: "Unknown", 1: "On", 2: "Off", 3: "Disabled"}.get(radio.state, "Unknown")
            print(f"  - {radio.name}: Kind={kind_name}, State={state_name}")
            
            if radio.kind == RadioKind.BLUETOOTH:
                print(f"    [TEST] Attempting to toggle Bluetooth...")
                try:
                    # Try to turn it off
                    result = await radio.set_state_async(RadioState.OFF)
                    print(f"    [RESULT] set_state_async returned: {result}")
                except Exception as e:
                    print(f"    [ERROR] Failed to toggle: {e}")
                    
    except ImportError as e:
        print(f"[ERROR] winsdk not installed: {e}")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_radios())
