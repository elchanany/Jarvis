"""
Hammer 2.1 -> OpenVINO (Safe Python API Method)
==============================================
Bypasses the 'optimum-cli' bug by using the Python API directly with trust_remote_code.
"""
from optimum.intel.openvino import OVModelForCausalLM
from transformers import AutoTokenizer
import os

model_id = "MadeAgents/Hammer2.1-3b"
output_dir = "models/hammer-2.1-3b-openvino"

def main():
    print("=" * 60)
    print(f"  🚀 Safe Downloading: {model_id} -> OpenVINO")
    print("=" * 60)
    
    if os.path.exists(output_dir):
        import shutil
        print(f"🧹 Clearing old directory: {output_dir}")
        shutil.rmtree(output_dir)
        
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        print("\n1. Loading Tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        
        print("\n2. Downloading and Exporting Model (This will take a while)...")
        # We export without heavy INT8 logic right now to avoid the 'stoll' bug.
        model = OVModelForCausalLM.from_pretrained(
            model_id, 
            export=True, 
            compile=False,
            trust_remote_code=True
        )
        
        print("\n3. Saving to disk...")
        tokenizer.save_pretrained(output_dir)
        model.save_pretrained(output_dir)
        
        print("\n✅ Success! Hammer is downloaded.")
        
    except Exception as e:
        print(f"\n❌ Error during safe export: {e}")

if __name__ == "__main__":
    main()
