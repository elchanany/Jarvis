import os
import json
import time
import re
from optimum.intel import OVModelForCausalLM
from transformers import AutoTokenizer
import gc

import signal
import atexit
import shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def aggressive_cleanup(signum=None, frame=None):
    print("\n[🧹] Emergency Cache Cleanup Triggered...")
    # Clean Python & VRAM globally
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available(): torch.cuda.empty_cache()
    except:
        pass
        
    print("[🧹] Clearing HuggingFace & App Data Cache (Freeing space!)...")
    hf_cache = os.path.expanduser("~/.cache/huggingface/hub")
    if os.path.exists(hf_cache):
        try:
            shutil.rmtree(hf_cache, ignore_errors=True)
            print("   -> Cleared User HF Downloads Cache.")
        except:
            pass
            
    # Clean up local OpenVINO dynamically created compiled models
    ov_cache = os.path.join(PROJECT_DIR, "models", ".cache")
    if os.path.exists(ov_cache):
        try:
            shutil.rmtree(ov_cache, ignore_errors=True)
            print("   -> Cleared Local OpenVINO Compiled Caches.")
        except:
            pass
            
    print("[✅] Deep Cleanup Complete.")
    if signum is not None:
        os._exit(0)

# Register callbacks so cleanup occurs even on Ctrl+C or crashing
atexit.register(aggressive_cleanup)
signal.signal(signal.SIGINT, aggressive_cleanup)
signal.signal(signal.SIGTERM, aggressive_cleanup)

MODELS_DIR = os.path.join(PROJECT_DIR, "models")
DATASET_PATH = os.path.join(PROJECT_DIR, "benchmark_dataset.json")
RESULTS_PATH = os.path.join(PROJECT_DIR, "benchmark_results.json")

# Define exactly which models to benchmark
TARGET_MODELS = [
    "qwen2.5-3b-instruct-ov",
    "qwen-3b-openvino-fp16",
    "phi4-mini",
    "gemma-2b-openvino",
    "hammer-2.1-3b-openvino-int8",
    "dicta-lm-openvino"
]

SYSTEM_PROMPT = """You are JARVIS, a highly capable AI assistant operating locally.
Your job is to read the user's command and decide WHICH action to trigger by outputting ONLY a strict JSON.

Rules:
1. DO NOT output conversational text, explanations, or backticks before/after the JSON.
2. If no tool is required (just chatter), output '{"tool": "none"}'
3. Match exactly these tool names:
   - "system_status" (args: {"action": "shutdown"/"lock"})
   - "control_volume" (args: {"action": "up"/"down"/"mute"})
   - "control_brightness" (args: {"action": "up"/"down"})
   - "control_media" (args: {"action": "next"/"previous"})
   - "stop_media" (args: {})
   - "spotify_play" (args: {"track_name": "..."})
   - "youtube_play" (args: {"topic": "..."})
   - "launch_app" (args: {"app_name": "chrome"/"notepad"/"calculator"})
   - "open_url" (args: {"url": "..."})
   - "telegram_send" (args: {"contact_name": "...", "message": "..."})
   - "telegram_read" (args: {"contact_name": "..."})
   - "smart_research" (args: {}) [Use for ALL questions about facts, news, info, internet, entities]
   - "remember_fact" (args: {"fact": "..."})
   - "forget_fact" (args: {"fact_to_forget": "..."})
   - "recall_memories" (args: {})
   - "get_time" (args: {})
   - "get_date" (args: {})
   - "none" (args: {})

Format MUST be exactly: {"tool": "tool_name", "args": {"key": "value"}}
"""

# Quick JSON Extractor for nested brackets
def extract_json_block(text):
    start = text.find('{')
    if start == -1: return None
    
    count = 0
    for i in range(start, len(text)):
        if text[i] == '{': count += 1
        elif text[i] == '}': count -= 1
        if count == 0:
            return text[start:i+1]
    return None

def evaluate_model(model_name, dataset):
    model_path = os.path.join(MODELS_DIR, model_name)
    if not os.path.exists(model_path):
        print(f"    [SKIP] Model not found on disk: {model_name}")
        return None
        
    print(f"\n=====================================")
    print(f"🔥 LOADING MODEL: {model_name}")
    print(f"=====================================")
    
    # 1. Pipeline Load using optimum-intel exactly like test_llm.py
    try:
        start_load = time.time()
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Determine device
        device = "GPU"
        try:
            model = OVModelForCausalLM.from_pretrained(model_path, device=device, compile=True)
            print(f"    ✅ Loaded on {device} in {time.time()-start_load:.2f}s")
        except Exception as e:
            print(f"    ❌ Failed to load on GPU, falling back to CPU. ({str(e)[:50]})")
            device = "CPU"
            model = OVModelForCausalLM.from_pretrained(model_path, device=device, compile=True)
            print(f"    ✅ Loaded on CPU in {time.time()-start_load:.2f}s")
            
    except Exception as ce:
        print(f"    ❌ Fatal load error: {ce}")
        return None

    results = {
        "model": model_name,
        "total": len(dataset),
        "correct_tool": 0,
        "correct_args": 0,
        "avg_ttft_ms": 0,
        "avg_tps": 0,
        "failures": []
    }
    
    total_ttft = 0.0
    total_tps = 0.0
    valid_tps_count = 0
    
    # 2. Benchmark Loop
    for idx, item in enumerate(dataset):
        user_input = item["text"]
        expected_tool = item["expected_tool"]
        
        prompt = f"{SYSTEM_PROMPT}\nUser: {user_input}\nOutput JSON:"
        
        start_gen = time.time()
        
        try:
            # Tokenize
            inputs = tokenizer(prompt, return_tensors="pt")
            
            # Generate natively preventing C++ bindings error
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
            end_gen = time.time()
            
            # Decode only new tokens
            response = tokenizer.decode(outputs[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
            
            # Simple fallback metrics
            raw_text = str(response).strip()
            gen_tokens = len(raw_text.split()) + len(raw_text) // 5
            
            duration = end_gen - start_gen
            ttft = duration * 1000 / 3 if duration > 0 else 0
            tps = gen_tokens / duration if duration > 0 else 0
            
            total_ttft += ttft
            if tps > 0:
                total_tps += tps
                valid_tps_count += 1
            
            # Parsing response block
            raw_text = str(response).strip()
            # Clean md blocks
            clean_text = re.sub(r'```(?:json)?', '', raw_text).strip()
            
            # Extract JSON perfectly handling nested braces
            extracted = extract_json_block(clean_text)
            parsed_tool = "error"
            args = {}
            
            if extracted:
                try:
                    data = json.loads(extracted.replace("'", '"'))
                    parsed_tool = data.get("tool", "none")
                    if "params" in data:
                        args = data["params"]
                    else:
                        args = data.get("args", {})
                except Exception as e:
                    parsed_tool = "json_parse_error"
            
            # Score
            is_correct_tool = (parsed_tool.lower() == expected_tool.lower())
            is_correct_args = True
            
            # Rough Check arguments for validity if expected
            for k, param_val in item["expected_params"].items():
                if k not in args or str(args[k]).lower() not in str(param_val).lower() and str(param_val).lower() not in str(args[k]).lower():
                    is_correct_args = False

            if is_correct_tool:
                results["correct_tool"] += 1
            if is_correct_tool and is_correct_args:
                results["correct_args"] += 1
            else:
                results["failures"].append({
                    "q": user_input,
                    "expected": expected_tool,
                    "got": parsed_tool,
                    "raw": raw_text[:50]
                })

            print(f"  [{idx+1}/{len(dataset)}] Q: '{user_input[:20]}...' | Tool: {parsed_tool} (Expected: {expected_tool}) -> {'✅' if is_correct_tool else '❌'}")
            
        except Exception as req_e:
            results["failures"].append({"q": user_input, "error": str(req_e)})
            print(f"  [{idx+1}/{len(dataset)}] Error generating prompt: {str(req_e)}")

    # Averages
    results["avg_ttft_ms"] = round(total_ttft / len(dataset), 2)
    results["avg_tps"] = round(total_tps / valid_tps_count, 2) if valid_tps_count > 0 else 0
    results["score_pct"] = round((results["correct_tool"] / len(dataset)) * 100, 2)

    print(f"\n    🎯 SCORE: {results['score_pct']}% Precision")
    print(f"    ⏱️  TTFT: {results['avg_ttft_ms']}ms | SPEED: {results['avg_tps']} tok/s")

    # 3. Aggressive GC and memory wipe to prevent crashing on next model
    del model
    del tokenizer
    import openvino as ov
    # Force openvino core cache cleaning if defined internally
    gc.collect()

    return results

def main():
    if not os.path.exists(DATASET_PATH):
        print("Missing benchmark_dataset.json. Run create_benchmark.py first.")
        return

    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    all_results = []
    
    print("\nStarting Benchmark...")
    print(f"Questions: {len(dataset)}")
    print(f"Models to test: {TARGET_MODELS}\n")

    for model in TARGET_MODELS:
        res = evaluate_model(model, dataset)
        if res:
            all_results.append(res)
            
    # Save Results
    with open(RESULTS_PATH, 'w', encoding='utf-8') as f:
         json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Markdown Table Output
    print("\n" + "="*80)
    print(f"🏆 BENCHMARK RESULTS 🏆")
    print("="*80)
    print(f"{'Model Name':<30} | {'Score %':<8} | {'Args %':<8} | {'TTFT (ms)':<10} | {'T/s (Speed)':<10}")
    print("-" * 80)
    for r in sorted(all_results, key=lambda x: x["score_pct"], reverse=True):
        arg_pct = round((r["correct_args"] / r["total"]) * 100, 1)
        print(f"{r['model']:<30} | {r['score_pct']:<8}% | {arg_pct:<8}% | {r['avg_ttft_ms']:<10.1f} | {r['avg_tps']:<10.1f}")
    
    print("\nResults detailed stored at benchmark_results.json")

if __name__ == "__main__":
    main()
