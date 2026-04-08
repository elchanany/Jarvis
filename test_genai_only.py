import sys
import os
import time

print("----------------------------------------------------------------")
print("   TEST: OpenVINO GenAI Import Isolation")
print("----------------------------------------------------------------")

print(f"[DEBUG] Python: {sys.version}")

try:
    print("[STEP 1] Importing openvino...")
    import openvino as ov
    print(f"[SUCCESS] OpenVINO version: {ov.__version__}")
except Exception as e:
    print(f"[FAIL] OpenVINO import failed: {e}")
    sys.exit(1)

print("[STEP 2] Importing openvino_genai (The likely freeze point)...")
print("        If it freezes here, you are missing Visual C++ Redistributables.")
start = time.time()
try:
    import openvino_genai
    print(f"[SUCCESS] OpenVINO GenAI imported in {time.time()-start:.2f}s")
except ImportError as e:
    print(f"[FAIL] GenAI Import Error: {e}")
except Exception as e:
    print(f"[FAIL] GenAI General Error: {e}")

print("----------------------------------------------------------------")
print("   TEST COMPLETE")
print("----------------------------------------------------------------")
