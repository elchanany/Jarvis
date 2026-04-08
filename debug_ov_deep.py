import sys
import os
import ctypes
import glob

print("=== DEEP DIAGNOSTIC FOR OPENVINO ===")
print(f"Python: {sys.version}")
print(f"Executable: {sys.executable}")

# 1. Check Site-Packages
print("\n--- Site Packages Search ---")
import site
site_packages = site.getsitepackages()[0]
ov_dir = os.path.join(site_packages, "openvino")
print(f"Checking {ov_dir}...")
if os.path.exists(ov_dir):
    print("  [OK] OpenVINO directory exists.")
    dlls = glob.glob(os.path.join(ov_dir, "*.dll")) + glob.glob(os.path.join(ov_dir, "libs", "*.dll")) + glob.glob(os.path.join(ov_dir, "bin", "*.dll"))
    print(f"  Found {len(dlls)} DLLs.")
else:
    print("  [FAIL] OpenVINO directory NOT found in site-packages!")

# 2. Check Dependencies (VC++)
print("\n--- DLL Dependency Check ---")
try:
    kernel32 = ctypes.windll.kernel32
    print("  [OK] Kernel32 accessible.")
    # vc_runtime = ctypes.cdll.LoadLibrary("vcruntime140.dll") # Test VC++
    # print("  [OK] VCRuntime140.dll loaded.")
except Exception as e:
    print(f"  [WARN] Basic DLL check warning: {e}")

# 3. Manual DLL Load Test (Risky Step)
print("\n--- Manual Load Test ---")
if os.path.exists(ov_dir):
    # Try adding to PATH explicitly before import
    libs_dir = os.path.join(ov_dir, "libs")
    bin_dir = os.path.join(ov_dir, "bin") # Some versions use bin
    
    new_path = libs_dir + ";" + bin_dir + ";" + os.environ["PATH"]
    os.environ["PATH"] = new_path
    print(f"  Added to PATH: {libs_dir}")
    
    # Try finding the main DLL
    main_dll = os.path.join(libs_dir, "openvino.dll")
    if not os.path.exists(main_dll):
         main_dll = os.path.join(ov_dir, "openvino.dll") # fallback
    
    if os.path.exists(main_dll):
        print(f"  Attempting to load: {main_dll}")
        try:
            lib = ctypes.CDLL(main_dll)
            print("  [SUCCESS] Main OpenVINO DLL loaded via ctypes!")
        except Exception as e:
            print(f"  [FAIL] DLL Load Failed: {e}")
            print("  This suggests missing system dependencies (like Visual C++ Redist 2015-2022).")
    else:
        print("  [WARN] Could not find openvino.dll to test.")

# 4. Verbose Import
print("\n--- Verbose Import ---")
try:
    print("  Importing openvino...")
    import openvino
    print("  [SUCCESS] import openvino passed.")
except ImportError as e:
    print(f"  [FAIL] Import Error: {e}")
except Exception as e:
    print(f"  [FAIL] General Error: {e}")

print("\n=== TEST COMPLETE ===")
