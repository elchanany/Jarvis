"""
Qwen2.5-3B → OpenVINO (NO Quantization - Debug Mode)
=====================================================
Exports without INT8/INT4 to test if quantization causes the "stoll" error.
"""

import os
import shutil
import subprocess

MODEL_ID = "Qwen/Qwen2.5-3B-Instruct"
OUTPUT_DIR = "models/qwen-3b-openvino-fp16"

def main():
    print("=" * 60)
    print("  🚀 Qwen2.5-3B → OpenVINO (FP16 - No Quantization)")
    print("=" * 60)
    
    # 1. Cleanup
    if os.path.exists(OUTPUT_DIR):
        print(f"\n🧹 Removing old model: {OUTPUT_DIR}")
        shutil.rmtree(OUTPUT_DIR)
    
    # 2. Export WITHOUT quantization
    print(f"\n⚙️  Converting {MODEL_ID} to FP16 (no compression)...")
    print("   This may take 5-10 minutes...")
    
    try:
        cmd = [
            "optimum-cli", "export", "openvino",
            "--model", MODEL_ID,
            "--task", "text-generation-with-past",
            # NO --weight-format flag = FP16
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
        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Conversion failed!")
        print(e.stderr[-500:] if len(e.stderr) > 500 else e.stderr)
        return
    
    print("\n" + "=" * 60)
    print(f"  ✅ Done! Model saved to: {OUTPUT_DIR}")
    print("  Note: This is FP16 (~5-6GB) - larger but might work")
    print("=" * 60)

if __name__ == "__main__":
    main()
