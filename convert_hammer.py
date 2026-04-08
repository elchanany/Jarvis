"""
Hammer 2.1 3B -> OpenVINO (CLI Method)
=====================================
Uses optimum-cli to convert MadeAgents/Hammer2.1-3b for local fast inference.
"""

import os
import shutil
import subprocess

MODEL_ID = "MadeAgents/Hammer2.1-3b"
OUTPUT_DIR = "models/hammer-2.1-3b-openvino-int8"

def main():
    print("=" * 60)
    print(f"  🚀 {MODEL_ID} -> OpenVINO INT8")
    print("=" * 60)
    
    # 1. Cleanup
    if os.path.exists(OUTPUT_DIR):
        print(f"\n🧹 Removing old model: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    
    # 2. Use optimum-cli
    print(f"\n⚙️  Converting {MODEL_ID} using optimum-cli...")
    print("   This may take 10-15 minutes depending on download speed...")
    
    try:
        # Run optimum-cli export command
        cmd = [
            "optimum-cli", "export", "openvino",
            "--model", MODEL_ID,
            "--task", "text-generation-with-past",
            "--weight-format", "int8",
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
        
        print("\n🔄 Trying without quantization (FP16)...")
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
            
        except subprocess.CalledProcessError as e2:
            print(f"\n❌ Both methods failed!")
            print(e2.stderr)
            return
    
    print("\n" + "=" * 60)
    print("  ✅ Done! Hammer is ready for Jarvis.")
    print("=" * 60)

if __name__ == "__main__":
    main()
