
print("Starting OpenVINO import test...")
try:
    import openvino as ov
    print("OpenVINO imported successfully.")
    print(f"Version: {ov.__version__}")
    
    import openvino_genai as ov_genai
    print("OpenVINO GenAI imported successfully.")
except Exception as e:
    print(f"Import failed: {e}")
print("Test complete.")
