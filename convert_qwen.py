"""
Qwen2.5-3B → OpenVINO (CLI Method - More Stable)
=================================================
Uses optimum-cli instead of Python API for better compatibility.
"""

import os
import shutil
import subprocess

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
OUTPUT_DIR = "models/qwen-3b-openvino-int4"

def main():
    print("=" * 60)
    print("  🚀 Qwen2.5-3B → OpenVINO (CLI Method)")
    print("=" * 60)
    
    # 1. Cleanup
    if os.path.exists(OUTPUT_DIR):
        print(f"\n🧹 Removing old model: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    
    # 2. Use optimum-cli (more stable than Python API)
    print(f"\n⚙️  Converting {MODEL_ID} using optimum-cli...")
    print("   This may take 5-10 minutes...")
    
    try:
        # Run optimum-cli export command
        cmd = [
            "optimum-cli", "export", "openvino",
            "--model", MODEL_ID,
            "--task", "text-generation-with-past",
            "--weight-format", "int8",  # INT8 instead of INT4
            OUTPUT_DIR
        ]
        
        print(f"\n📝 Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        
        print("\n✅ Conversion successful!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ CLI conversion failed!")
        print("Error output:")
        print(e.stderr)
        
        # Fallback: Try without weight compression
        print("\n🔄 Trying without quantization...")
        try:
            cmd_fallback = [
                "optimum-cli", "export", "openvino",
                "--model", MODEL_ID,
                "--task", "text-generation-with-past",
                OUTPUT_DIR
            ]
            
            result = subprocess.run(
                cmd_fallback,
                check=True,
                capture_output=True,
                text=True
            )
            
            print("\n✅ Fallback conversion successful (FP16)!")
            print("   Note: Model will be larger (~3GB) but should work")
            
        except subprocess.CalledProcessError as e2:
            print(f"\n❌ Both methods failed!")
            print(e2.stderr)
            return
    
    print("\n" + "=" * 60)
    print("  ✅ Done! Run: python test_llm.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
