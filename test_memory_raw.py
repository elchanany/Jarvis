import os
import time
import sys

# Setup paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PHI4_PATH = os.path.join(PROJECT_DIR, "models", "phi4-mini")

print(f"Loading model from: {PHI4_PATH}")

try:
    import openvino as ov
    # Fix OpenVINO path for Windows
    ov_path = os.path.dirname(ov.__file__)
    os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ["PATH"]
    
    import openvino_genai as ov_genai
except ImportError:
    print("Error: OpenVINO not installed or dlls missing.")
    sys.exit(1)

def load_model():
    print("Initializing LLM Pipeline...")
    start = time.time()
    try:
        # Try GPU first
        config = {"CACHE_DIR": "./model_cache"}
        pipeline = ov_genai.LLMPipeline(PHI4_PATH, device="GPU", **config)
        print(f"Loaded on GPU in {time.time() - start:.2f}s")
        return pipeline
    except Exception as e:
        print(f"GPU failed: {e}")
        try:
            # Fallback to CPU
            pipeline = ov_genai.LLMPipeline(PHI4_PATH, device="CPU", **config)
            print(f"Loaded on CPU in {time.time() - start:.2f}s")
            return pipeline
        except Exception as e2:
            print(f"CPU failed: {e2}")
            return None

def main():
    pipeline = load_model()
    if not pipeline:
        return

    history = """You are a helpful assistant.
User: Hello
Assistant: Hi there! How can I help?
"""
    
    print("\n=== RAW MEMORY TEST (Type 'exit' to quit) ===")
    print("This connects DIRECTLY to the model, bypassing all Jarvis layers.")
    
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            # Add to history
            history += f"User: {user_input}\nAssistant:"
            
            # Generate
            print("Thinking...", end="", flush=True)
            start_gen = time.time()
            response = pipeline.generate(history, max_new_tokens=200)
            
            # Clean response
            # OpenVINO sometimes returns the full text or just the new part depending on version
            # Usually generate() returns just the new tokens text, but let's be safe
            if isinstance(response, str):
                text = response
            else:
                text = str(response)
                
            elapsed = time.time() - start_gen
            print(f"\rAssistant ({elapsed:.2f}s): {text}")
            
            # Add response to history for next turn
            history += f" {text}\n"
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()
