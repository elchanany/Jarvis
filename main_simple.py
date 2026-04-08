# Jarvis - Simple Terminal Chat
# ==============================
# Minimal version: LLM only, no voice, no tools
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
    
    # Build simple prompt (Phi-4 format uses special tokens)
    system_token = chr(60) + "|system|" + chr(62)
    end_token = chr(60) + "|end|" + chr(62)
    user_token = chr(60) + "|user|" + chr(62)
    assistant_token = chr(60) + "|assistant|" + chr(62)
    
    prompt = system_token + "You are Jarvis. Be concise and helpful." + end_token + "\n"
    prompt += user_token + message + end_token + "\n"
    prompt += assistant_token
    
    try:
        start = time.time()
        response = phi4_pipeline.generate(prompt, max_new_tokens=200)
        elapsed = time.time() - start
        
        # Extract text from response
        if hasattr(response, 'text'):
            text = response.text
        else:
            text = str(response)
        
        print("[DEBUG] Generated in {:.2f}s".format(elapsed))
        return text.strip()
    except Exception as e:
        return "[ERROR] " + str(e)

def main():
    print("=" * 50)
    print("   JARVIS - Simple Terminal Chat")
    print("=" * 50)
    
    # Initialize
    init_openvino()
    
    if not load_llm():
        print("[FATAL] Cannot load LLM. Exiting.")
        return
    
    print("\n[READY] Type your message. Type 'exit' to quit.\n")
    
    # Chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break
            
            # Get response from LLM
            print("Jarvis: ", end="", flush=True)
            response = chat(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print("[ERROR] " + str(e))

if __name__ == "__main__":
    main()
