"""
Qwen2.5-3B Benchmark - Using optimum-intel (Alternative Loader)
================================================================
Uses OVModelForCausalLM instead of openvino_genai.LLMPipeline
to avoid the "stoll argument out of range" bug.
"""

import os
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(PROJECT_DIR, "models", "qwen-3b-openvino-int4")

def load_model():
    print(f"⏳ Loading Qwen2.5-3B from: {MODEL_PATH}")
    start_load = time.time()
    
    try:
        # Use optimum-intel instead of openvino_genai
        from optimum.intel import OVModelForCausalLM
        from transformers import AutoTokenizer
        
        print("   Loading with optimum-intel (OVModelForCausalLM)...")
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        
        # Load model - try different devices
        for device in ["GPU", "CPU"]:
            try:
                print(f"   Attempting {device}...")
                model = OVModelForCausalLM.from_pretrained(
                    MODEL_PATH,
                    device=device,
                    compile=True
                )
                load_time = time.time() - start_load
                print(f"✅ Loaded on {device} in {load_time:.2f}s")
                return model, tokenizer, device
            except Exception as e:
                print(f"   ❌ {device} failed: {str(e)[:60]}")
        
        return None, None, None
        
    except ImportError as e:
        print(f"❌ Missing library: {e}")
        return None, None, None

def main():
    print("==========================================")
    print("   🧪 JARVIS LLM BENCHMARK (Qwen2.5-3B)")
    print("   Using: optimum-intel loader")
    print("==========================================")
    
    model, tokenizer, device = load_model()
    
    if model is None:
        print("❌ Could not load model. Exiting.")
        return

    print("\n💡 Type 'exit' to quit.")
    print("   Enter your text prompt (Hebrew/English).")

    while True:
        try:
            user_input = input("\n📝 You: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input.strip():
                continue

            # Construct prompt (Qwen chat format)
            messages = [{"role": "user", "content": user_input}]
            prompt = tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            print("   (Generating...)")
            
            # Tokenize
            inputs = tokenizer(prompt, return_tensors="pt")
            
            # Generate
            start_gen = time.time()
            outputs = model.generate(
                **inputs,
                max_new_tokens=200,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id
            )
            end_gen = time.time()
            
            # Decode
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Remove the prompt from response
            if prompt in response:
                response = response.replace(prompt, "").strip()
            
            total_time = end_gen - start_gen
            output_words = len(response.split())
            
            print(f"\n🤖 Qwen: {response}")
            print("\n📊 --- STATS ---")
            print(f"   ⏱️ Total Time:     {total_time:.4f} sec")
            print(f"   ⚡ Speed:          ~{len(response) / total_time:.1f} chars/sec")
            print(f"   📏 Output Length:  {output_words} words")
            print(f"   🖥️ Device:         {device}")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
