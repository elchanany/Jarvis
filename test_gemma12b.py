import os
import json
import time
import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_PATH = r"C:\AI\Wan2GP\ckpts\gemma-3-12b-it-qat-q4_0-unquantized"
DATASET_PATH = "benchmark_dataset.json"

SYSTEM_PROMPT = """You are JARVIS, a highly capable AI assistant operating locally.
Your job is to read the user's command and decide WHICH action to trigger by outputting ONLY a strict JSON.

Rules:
1. DO NOT output conversational text, explanations, or backticks before/after the JSON.
2. If no tool is required (just chatter), output '{"tool": "none"}'
3. Match exactly these tool names:
   - "system_status" (args: {"action": "shutdown"/"lock"})
   - "control_volume" (args: {"action": "up"/"down"/"mute"})
   - "control_media" (args: {"action": "next"/"previous"})
   - "stop_media" (args: {})
   - "spotify_play" (args: {"track_name": "..."})
   - "youtube_play" (args: {"topic": "..."})
   - "launch_app" (args: {"app_name": "chrome"/"notepad"/"calculator"})
   - "open_url" (args: {"url": "..."})
   - "smart_research" (args: {}) [Use for ALL questions about facts, news, info, internet, entities]
   - "remember_fact" (args: {"fact": "..."})
   - "forget_fact" (args: {"fact_to_forget": "..."})
   - "recall_memories" (args: {})
   - "get_time" (args: {})
   - "get_date" (args: {})
   - "none" (args: {})

Format MUST be exactly: {"tool": "tool_name", "args": {"key": "value"}}"""

def main():
    print("="*60)
    print(" 🚀 BENCHMARK & CHAT: GEMMA-3-12B ")
    print("="*60)
    
    print(f"\n[1/3] Loading Tokenizer...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    except Exception as e:
        print(f"❌ Failed to load Tokenizer. Error: {e}")
        return
        
    print(f"[2/3] Loading 12B Model... (Warning: Using 13GB+ of RAM!)")
    start_load = time.time()
    try:
        # Load raw PyTorch model, distributing to GPU/CPU memory as needed
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="auto",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True
        )
    except Exception as e:
        print(f"❌ Failed to load Model! {e}")
        return
        
    print(f"✅ Model Loaded Successfully in {time.time()-start_load:.1f}s.")
    
    if not os.path.exists(DATASET_PATH):
        print(f"❌ '{DATASET_PATH}' missing. Please generate the dataset first.")
        return
        
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    print("\n[3/3] --- Starting 100 Questions Benchmark ---")
    correct_tool = 0
    total_ttft = 0.0
    total_tps = 0.0
    
    for idx, item in enumerate(dataset):
        user_input = item["text"]
        expected_tool = item["expected_tool"]
        
        # Format the user intent prompt
        messages = [
            {"role": "user", "content": f"{SYSTEM_PROMPT}\nUser: {user_input}\nOutput JSON:"}
        ]
        
        try:
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception:
            # Fallback if chat template isn't properly defined for Gemma in this format
            prompt = f"{SYSTEM_PROMPT}\nUser: {user_input}\nOutput JSON:\n"
            
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        start_gen = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.1,
                pad_token_id=tokenizer.eos_token_id
            )
        end_gen = time.time()
        
        # Calculate tokens and speeds
        gen_tokens = len(outputs[0]) - len(inputs.input_ids[0])
        raw_text = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
        raw_text = raw_text.strip()
        
        duration = end_gen - start_gen
        tps = gen_tokens / duration if duration > 0 else 0
        ttft = duration * 1000 / 3 if duration > 0 else 0
        
        total_ttft += ttft
        total_tps += tps
        
        # Extract intent safely
        clean_text = re.sub(r'```(?:json)?', '', raw_text).strip()
        match = re.search(r'\{(?:[^{}]|(?-1))*\}', clean_text)
        parsed_tool = "error"
        if match:
            try:
                data = json.loads(match.group(0).replace("'", '"'))
                parsed_tool = data.get("tool", "none")
            except:
                parsed_tool = "parse_exception"
                
        is_correct_tool = (parsed_tool.lower() == expected_tool.lower())
        if is_correct_tool:
            correct_tool += 1
            
        status = '✅' if is_correct_tool else '❌'
        print(f" [{idx+1}/{len(dataset)}] Tool: {parsed_tool} (Expected: {expected_tool}) -> {status} | {tps:.1f} tok/s")

    # Benchmark Summary
    print("\n=============================================")
    print(f"🏆 Pytorch Benchmark Results (Gemma-3-12B)")
    print("=============================================")
    print(f"Score Precision:   {(correct_tool/len(dataset))*100:.1f}% ({correct_tool}/{len(dataset)})")
    print(f"Average Speed:     {total_tps/len(dataset):.1f} Tokens / Second")
    print(f"Average Latency:   {total_ttft/len(dataset):.1f} MS")
    print("=============================================\n")
    
    # -------------------------------------------
    # FREE CHAT MODE
    # -------------------------------------------
    print("💬 Entering Free Chat Mode. Talk to Gemma!")
    print("Type 'X' or 'x' and press Enter to exit.\n")
    
    # Simple history buffer
    chat_history = []
    
    while True:
        try:
            user_msg = input("You: ")
            if user_msg.strip().upper() == 'X':
                print("\nExiting chat and releasing memory... Goodbye!")
                break
                
            chat_history.append({"role": "user", "content": user_msg})
            
            try:
                prompt = tokenizer.apply_chat_template(chat_history, tokenize=False, add_generation_prompt=True)
            except:
                prompt = f"User: {user_msg}\nAssistant: "
                
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            
            s = time.time()
            with torch.no_grad():
                outputs = model.generate(
                    **inputs, 
                    max_new_tokens=400, 
                    temperature=0.7,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            resp = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True).strip()
            e = time.time()
            
            print(f"Gemma 12B: {resp}\n  (Took {e-s:.1f}s)")
            
            chat_history.append({"role": "assistant", "content": resp})
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
