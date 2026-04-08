# Script to create main_simple.py
code = r'''# Jarvis - Simple Terminal Chat
# Run: python main_simple.py

import os
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PHI4_PATH = os.path.join(PROJECT_DIR, "models", "phi4-mini")

phi4_pipeline = None

def init_openvino():
    try:
        import openvino as ov
        ov_path = os.path.dirname(ov.__file__)
        os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ["PATH"]
        print("[OK] OpenVINO ready")
        return True
    except ImportError:
        print("[WARN] OpenVINO not found")
        return False

def load_llm():
    global phi4_pipeline
    import openvino_genai as ov_genai
    
    if not os.path.exists(PHI4_PATH):
        print("[ERROR] Model not found: " + PHI4_PATH)
        return False
    
    print("[INFO] Loading Phi-4...")
    start = time.time()
    
    for device in ["GPU", "CPU"]:
        try:
            config = {"CACHE_DIR": "./model_cache"}
            phi4_pipeline = ov_genai.LLMPipeline(PHI4_PATH, device=device, **config)
            elapsed = time.time() - start
            print("[OK] Loaded on {} in {:.2f}s".format(device, elapsed))
            return True
        except Exception as e:
            print("[WARN] {} failed: {}".format(device, str(e)[:40]))
    
    return False

def chat(message):
    if phi4_pipeline is None:
        return "LLM not loaded"
    
    prompt = "<|system|>You are Jarvis. Be concise and helpful.<|end|>\n"
    prompt += "
