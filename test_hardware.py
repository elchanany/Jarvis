import os
import sys

try:
    import psutil
except ImportError:
    print("Installing psutil for hardware detection...")
    os.system("pip install psutil")
    import psutil

import platform
import subprocess

def get_system_info():
    print("========================================")
    print("      Jarvis System Hardware Test       ")
    print("========================================")
    print()
    
    # OS
    print(f"[+] OS: {platform.system()} {platform.release()}")
    
    # CPU
    print(f"[+] CPU: {platform.processor()}")
    print(f"    - Physical Cores: {psutil.cpu_count(logical=False)}")
    print(f"    - Total Threads: {psutil.cpu_count(logical=True)}")
    
    # RAM
    ram = psutil.virtual_memory()
    total_ram_gb = ram.total / (1024**3)
    print(f"[+] Total RAM: {total_ram_gb:.2f} GB")
    print(f"    - Available: {ram.available / (1024**3):.2f} GB")
    
    # GPU (Windows)
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        gpu_info = subprocess.check_output(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            startupinfo=startupinfo,
            text=True
        )
        print("\n[+] GPU(s) Detected:")
        gpu_lines = [line.strip() for line in gpu_info.split('\n') if line.strip() and "Name" not in line.strip()]
        if not gpu_lines:
            print("    - None found or drivers missing.")
        for gpu in gpu_lines:
            print(f"    - {gpu}")
    except Exception as e:
        print(f"    [!] Could not detect GPU directly via wmic: {e}")

    print("\n========================================")
    print("       Hardware Check Complete!         ")
    print("========================================")

if __name__ == '__main__':
    get_system_info()
