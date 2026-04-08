import os
import time
import sys

# DEBUG LOGGING PREAMBLE
print("----------------------------------------------------------------")
print("   QWEN 2.5 STANDALONE CHAT TEST")
print("----------------------------------------------------------------")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
QWEN_PATH = os.path.join(PROJECT_DIR, "models", "qwen2.5-3b-instruct-ov")
CACHE_DIR = os.path.join(PROJECT_DIR, "model_cache")

print(f"[DEBUG] Model Path: {QWEN_PATH}")
print(f"[DEBUG] Cache Path: {CACHE_DIR}")

if not os.path.exists(QWEN_PATH):
    print("[ERROR] Model path does not exist!")
    sys.exit(1)

print("[DEBUG] Importing OpenVINO...")
try:
    import openvino as ov
    ov_path = os.path.dirname(ov.__file__)
    print(f"[DEBUG] OpenVINO Path: {ov_path}")
    # Add libs to PATH
    os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ["PATH"]
    
    import openvino_genai as ov_genai
    print("[DEBUG] OpenVINO GenAI imported successfully.")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

def main():
    # Switch to GPU for speed now that we know it works
    device = "GPU"
    print(f"[DEBUG] Attempting to load model on {device}...")
    
    config = {"CACHE_DIR": CACHE_DIR}
    if not os.path.exists(CACHE_DIR):
        print("[DEBUG] Creating cache directory...")
        os.makedirs(CACHE_DIR, exist_ok=True)
    
    start_time = time.time()
    try:
        # Initialize pipeline
        print("[DEBUG] Initializing LLMPipeline...")
        pipe = ov_genai.LLMPipeline(QWEN_PATH, device=device, **config)
        print(f"[SUCCESS] Model loaded in {time.time() - start_time:.2f}s")
        
        print("\n==========================================")
        print(" CHAT STARTED (Type 'exit' to quit)")
        print("==========================================\n")
        
        history = []
        
        while True:
            try:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                
                print("Thinking...", end="", flush=True)
                
                # generate
                response = pipe.generate(user_input, max_new_tokens=200)
                
                # Clean up response if needed (sometimes returns the full prompt)
                if response.startswith(user_input):
                    response = response[len(user_input):].strip()
                    
                print(f"\rJarvis: {response}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n[ERROR] Generation failed: {e}")

    except Exception as e:
        print(f"\n[FATAL] Failed to load model: {e}")
        print("Try falling back to CPU if this persists.")

if __name__ == "__main__":
    main()
