"""
Convert Helsinki-NLP translation models to CTranslate2 format.
Run this once to create the fast models.
"""
import os
import sys

def convert_models():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(base_dir, "models")
    os.makedirs(models_dir, exist_ok=True)
    
    try:
        import ctranslate2
        from transformers import MarianMTModel, MarianTokenizer
    except ImportError:
        print("Please install: pip install ctranslate2 transformers")
        return
    
    # Models to convert
    models = [
        ("Helsinki-NLP/opus-mt-tc-big-he-en", "translation-he-en-ct2"),
        ("Helsinki-NLP/opus-mt-en-he", "translation-en-he-ct2"),
    ]
    
    for hf_model_name, output_name in models:
        output_path = os.path.join(models_dir, output_name)
        if os.path.exists(output_path):
            print(f"[SKIP] {output_name} already exists")
            continue
            
        print(f"[CONVERTING] {hf_model_name} -> {output_name}...")
        
        try:
            # Download model and tokenizer from Hugging Face
            print(f"  [1/3] Downloading {hf_model_name}...")
            model = MarianMTModel.from_pretrained(hf_model_name)
            tokenizer = MarianTokenizer.from_pretrained(hf_model_name)
            
            # Save locally first
            temp_dir = os.path.join(models_dir, f"temp_{output_name}")
            os.makedirs(temp_dir, exist_ok=True)
            print(f"  [2/3] Saving to temp directory...")
            model.save_pretrained(temp_dir)
            tokenizer.save_pretrained(temp_dir)
            
            # Convert using CTranslate2 Python API
            print(f"  [3/3] Converting to CTranslate2...")
            converter = ctranslate2.converters.TransformersConverter(temp_dir)
            converter.convert(output_path, quantization="int8")
            
            print(f"[DONE] {output_name} created!")
            
            # Clean up temp dir
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            print(f"[ERROR] Failed to convert {hf_model_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n[COMPLETE] Conversion finished.")
    print("Restart Jarvis to use the fast CTranslate2 models!")

if __name__ == "__main__":
    convert_models()
