import os
import json
import subprocess
from huggingface_hub import snapshot_download

MODEL_ID = "MadeAgents/Hammer2.1-3b"
LOCAL_TEMP_DIR = "models/hammer-pytorch-temp"
OUTPUT_DIR = "models/hammer-2.1-3b-openvino-int8"

def main():
    print("=============================================================")
    print(f" 1. Downloading Raw PyTorch Model: {MODEL_ID}")
    print("=============================================================")
    print("Please wait, downloading ~6GB...")
    try:
        snapshot_download(
            repo_id=MODEL_ID,
            local_dir=LOCAL_TEMP_DIR,
            local_dir_use_symlinks=False
        )
        print("✅ Download complete.")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return

    print("\n=============================================================")
    print(" 2. Patching config.json (Fixing the OpenVINO bug)")
    print("=============================================================")
    config_path = os.path.join(LOCAL_TEMP_DIR, "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            # The 'rope_scaling' key with YaRN in new Qwen 2.5 causes OpenVINO XML export to corrupt
            # and throw the "stoll argument out of range" / "Tags mismatch" C++ error.
            if "rope_scaling" in config:
                print(f"   🔧 Removing problematic rope_scaling config...")
                del config["rope_scaling"]
                
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                print("   ✅ config.json patched successfully!")
            else:
                print("   ℹ️ No rope_scaling found, skipping patch.")
        except Exception as e:
            print(f"   ❌ Error patching config: {e}")
    else:
        print("   ❌ config.json not found in downloaded files!")

    print("\n=============================================================")
    print(" 3. Exporting to OpenVINO INT8 using patched files")
    print("=============================================================")
    print("This will take a few minutes...")
    try:
        cmd = [
            "optimum-cli", "export", "openvino",
            "--model", LOCAL_TEMP_DIR,
            "--task", "text-generation-with-past",
            "--weight-format", "int8",
            "--trust-remote-code",
            OUTPUT_DIR
        ]
        
        print(f"📝 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False)
        
        if result.returncode == 0:
            print("\n✅ SUCCESS! Hammer 2.1 is fully converted and ready!")
            import shutil
            # Clean up PyTorch temp files to save 6GB of disk space
            print("🧹 Cleaning up temporary PyTorch files...")
            try:
                shutil.rmtree(LOCAL_TEMP_DIR)
            except:
                pass
        else:
            print("\n❌ Export failed. Please check the terminal output above.")
            
    except Exception as e:
        print(f"\n❌ Error running optimum-cli: {e}")

if __name__ == "__main__":
    main()
