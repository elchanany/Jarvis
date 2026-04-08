import os
import urllib.request
import tarfile
import shutil

MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2"
DEST_FILE = "kokoro.tar.bz2"
MODELS_DIR = "models"

def download_and_extract():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        
    print(f"⬇️ Downloading Kokoro model from {MODEL_URL}...")
    try:
        urllib.request.urlretrieve(MODEL_URL, os.path.join(MODELS_DIR, DEST_FILE))
        print("✅ Download complete.")
    except Exception as e:
        print(f"❌ Download failed: {e}")
        return

    print("📦 Extracting model...")
    try:
        with tarfile.open(os.path.join(MODELS_DIR, DEST_FILE), "r:bz2") as tar:
            tar.extractall(path=MODELS_DIR)
        print("✅ Extraction complete.")
        
        # Cleanup
        os.remove(os.path.join(MODELS_DIR, DEST_FILE))
        print("🧹 Cleanup done.")
        
        print(f"\n🎉 Model is ready in: {os.path.join(MODELS_DIR, 'kokoro-multi-lang-v1_0')}")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")

if __name__ == "__main__":
    download_and_extract()
