import os
import shutil
from optimum.intel import OVModelForSpeechSeq2Seq
from transformers import AutoProcessor
from openvino_tokenizers import convert_tokenizer
from openvino import save_model

MODEL_ID = "mike249/whisper-small-he-v4"
OUTPUT_DIR = "models/whisper-small-he-openvino"

def main():
    # 1. Cleanup (Only model files, keep dir if exists)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # 2. Export (Stateful)
    print(f"🚀 Exporting {MODEL_ID} to OpenVINO...")
    
    try:
        model = OVModelForSpeechSeq2Seq.from_pretrained(
            MODEL_ID,
            export=True,
            compile=False,
            stateful=True,  # <--- CRITICAL for NPU
            use_cache=True,
            load_in_8bit=True 
        )
    except TypeError:
        print("   ⚠️  Direct 8-bit load not supported, loading FP32...")
        model = OVModelForSpeechSeq2Seq.from_pretrained(
            MODEL_ID,
            export=True,
            compile=False,
            stateful=True,
            use_cache=True
        )

    # 3. Save Model
    print(f"💾 Saving model to {OUTPUT_DIR}...")
    model.save_pretrained(OUTPUT_DIR)
    
    # 4. Processor & Tokenizer
    print("📝 Saving processor...")
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    processor.save_pretrained(OUTPUT_DIR)

    # 5. Convert Tokenizer to OpenVINO (Crucial for C++ pipeline!)
    print("🔧 Converting Tokenizer & Detokenizer (REQUIRED for Pipeline)...")
    try:
        # Convert tokenizer to OpenVINO model
        ov_tokenizer, ov_detokenizer = convert_tokenizer(processor.tokenizer, with_detokenizer=True)
        
        # Save them
        save_model(ov_tokenizer, os.path.join(OUTPUT_DIR, "openvino_tokenizer.xml"))
        save_model(ov_detokenizer, os.path.join(OUTPUT_DIR, "openvino_detokenizer.xml"))
        print("   ✅ Tokenizers saved successfully!")
    except Exception as e:
        print(f"   ❌ Tokenizer conversion failed: {e}") 
    
    print("\n✅ FULL Conversion Complete! Model + Tokenizers ready.")

if __name__ == "__main__":
    main()
