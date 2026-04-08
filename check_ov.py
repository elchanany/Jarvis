
import logging
import openvino.runtime as ov

def check_devices():
    core = ov.Core()
    devices = core.available_devices
    print(f"\n🔍 OpenVINO Available Devices: {devices}")
    
    for device in devices:
        print(f"   - {device}: {core.get_property(device, 'FULL_DEVICE_NAME')}")

if __name__ == "__main__":
    check_devices()
