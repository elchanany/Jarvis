import os
import shutil
import time
import openvino_genai as ov_genai

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "phi4-mini")
CACHE_DIR = "./model_cache"

def compile_model():
    print("="*60)
    print("   OPENVINO GPU MODEL COMPILER")
    print("="*60)
    
    # 1. Clean existing cache
    if os.path.exists(CACHE_DIR):
        print(f"[1/3] Clearing old cache at {CACHE_DIR}...")
        try:
            shutil.rmtree(CACHE_DIR)
            time.sleep(1) # Wait for OS to release files
            print("      ✓ Cache cleared")
        except Exception as e:
            print(f"      ❌ Could not clear cache: {e}")
            print("      Please ensure no other python processes are running.")
            return

    # 2. Compile
    print(f"[2/3] Compiling Phi-4 for GPU (This will take ~1-2 minutes)...")
    print("      Do NOT close this window.")
    
    try:
        start = time.time()
        # Initialize pipeline which triggers compilation and caching
        config = {"CACHE_DIR": CACHE_DIR}
        pipe = ov_genai.LLMPipeline(MODEL_PATH, device="GPU", **config)
        
        elapsed = time.time() - start
        print(f"      ✓ Compilation complete in {elapsed:.1f}s")
        
        # Verify cache was created
        if os.path.exists(CACHE_DIR) and len(os.listdir(CACHE_DIR)) > 0:
            print(f"[3/3] Verifying cache... OK ({len(os.listdir(CACHE_DIR))} files)")
            print("\nSUCCESS! You can now run 'main_brain.py' and it will load instantly.")
        else:
            print("\n⚠️ WARNING: Pipeline loaded but cache folder seems empty.")
            
    except Exception as e:
        print(f"\n❌ FATAL ERROR during compilation: {e}")
        print("Possible causes:")
        print("1. Not enough disk space (Need ~2-3GB free)")
        print("2. GPU driver issues")
        print("3. Permission denied (Try running as Administrator)")

if __name__ == "__main__":
    compile_model()
    input("\nPress Enter to exit...")
