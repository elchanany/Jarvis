
import os
import time
from pathlib import Path

def convert_models():
    print("="*60)
    print("   JARVIS - Translation Model Optimizer (OpenVINO)")
    print("="*60)
    print()
    
    # Check dependencies
    try:
        import optimum.intel.openvino
        from optimum.intel import OVModelForSeq2SeqLM
        from transformers import AutoTokenizer
        print("[CHECK] optimum-intel is installed.")
    except ImportError:
        print("[ERROR] 'optimum-intel' or 'openvino' not found.")
        print("Please run: pip install optimum[openvino]")
        return

    # Define models
    models_to_convert = [
        ("Helsinki-NLP/opus-mt-he-en", "models/translation-he-en-ov"),
        ("Helsinki-NLP/opus-mt-en-he", "models/translation-en-he-ov")
    ]
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    for model_id, save_path in models_to_convert:
        full_save_path = os.path.join(base_dir, save_path)
        
        if os.path.exists(full_save_path) and os.path.exists(os.path.join(full_save_path, "openvino_model.xml")):
            print(f"[SKIP] {model_id} already converted at {save_path}")
            continue
            
        print(f"\n[CONVERT] Converting {model_id}...")
        print("This may take 1-2 minutes...")
        start = time.time()
        
        try:
            # Load and export
            model = OVModelForSeq2SeqLM.from_pretrained(model_id, export=True)
            tokenizer = AutoTokenizer.from_pretrained(model_id)
            
            # Save
            model.save_pretrained(full_save_path)
            tokenizer.save_pretrained(full_save_path)
            
            print(f"[SUCCESS] Converted in {time.time()-start:.1f}s")
            print(f"[SAVED] {full_save_path}")
            
        except Exception as e:
            print(f"[ERROR] Failed to convert {model_id}: {e}")

    print("\n[DONE] All models ready. You can now restart 'main_brain.py'.")

if __name__ == "__main__":
    convert_models()
