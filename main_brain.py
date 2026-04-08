# main_brain.py
# ==============
# Jarvis Brain - With Model Selection & Full Logging
# + Hebrew Translation Layer

import os
import sys
import time
import re
from datetime import datetime
from langchain_core.messages import HumanMessage

from agent_state import create_initial_state
import brain
from jarvis_layers import generate_fallback_response, build_response_prompt

# Global reference to kernel for direct tool execution
_KERNEL = None

def get_sk_kernel():
    """Get or initialize the kernel for tool execution."""
    global _KERNEL
    if _KERNEL is None:
        from sk_kernel import get_kernel
        _KERNEL = get_kernel()
    return _KERNEL

def execute_tool(tool_name: str, tool_args: dict) -> str:
    """Execute a tool directly through the kernel."""
    kernel = get_sk_kernel()
    return kernel.execute_by_name(tool_name, **tool_args)


# import torch (Moved to inside function to save RAM)
# torch.set_num_threads(4) (Moved to inside function)

# Global translation models (loaded on first use)
_HE_EN_MODEL = None
_EN_HE_MODEL = None
_HE_EN_TOKENIZER = None
_EN_HE_TOKENIZER = None
_TRANSLATION_ENGINE = None  # "ctranslate2", "openvino", or "pytorch"

def is_hebrew(text: str) -> bool:
    """Check if text contains Hebrew characters."""
    hebrew_pattern = re.compile(r'[\u0590-\u05FF]')
    return bool(hebrew_pattern.search(text))

def load_translation_models():
    """Load translation models (tries CTranslate2 > OpenVINO > PyTorch)."""
    global _HE_EN_MODEL, _EN_HE_MODEL, _HE_EN_TOKENIZER, _EN_HE_TOKENIZER, _TRANSLATION_ENGINE
    
    if _HE_EN_MODEL is not None:
        return  # Already loaded
    
    print("[TRANSLATE] Loading Hebrew translation models...")
    start = time.time()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # === TRY 1: CTranslate2 (Fastest) ===
    try:
        import ctranslate2
        from transformers import AutoTokenizer
        
        ct2_he_en_path = os.path.join(base_dir, "models", "translation-he-en-ct2")
        ct2_en_he_path = os.path.join(base_dir, "models", "translation-en-he-ct2")
        
        if os.path.exists(ct2_he_en_path) and os.path.exists(ct2_en_he_path):
            print("[TRANSLATE] Found CTranslate2 models! Loading ultra-fast versions...")
            _HE_EN_MODEL = ctranslate2.Translator(ct2_he_en_path, device="cpu", compute_type="int8")
            _EN_HE_MODEL = ctranslate2.Translator(ct2_en_he_path, device="cpu", compute_type="int8")
            _HE_EN_TOKENIZER = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-tc-big-he-en")
            _EN_HE_TOKENIZER = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-he")
            _TRANSLATION_ENGINE = "ctranslate2"
            print(f"[TRANSLATE] CTranslate2 models loaded in {time.time()-start:.1f}s (FAST MODE)")
            return
    except ImportError:
        print("[TRANSLATE] CTranslate2 not installed, trying alternatives...")
    except Exception as e:
        print(f"[TRANSLATE] CTranslate2 failed: {e}")
    
    # === TRY 2: OpenVINO ===
    try:
        from optimum.intel import OVModelForSeq2SeqLM
        from transformers import AutoTokenizer
        
        he_en_path = os.path.join(base_dir, "models", "translation-he-en-ov")
        en_he_path = os.path.join(base_dir, "models", "translation-en-he-ov")
        
        if os.path.exists(he_en_path) and os.path.exists(en_he_path):
            print("[TRANSLATE] Found OpenVINO models! Loading fast versions...")
            _HE_EN_TOKENIZER = AutoTokenizer.from_pretrained(he_en_path)
            _HE_EN_MODEL = OVModelForSeq2SeqLM.from_pretrained(he_en_path, device="CPU")
            _EN_HE_TOKENIZER = AutoTokenizer.from_pretrained(en_he_path)
            _EN_HE_MODEL = OVModelForSeq2SeqLM.from_pretrained(en_he_path, device="CPU")
            _TRANSLATION_ENGINE = "openvino"
            print(f"[TRANSLATE] OpenVINO models loaded in {time.time()-start:.1f}s")
            return
    except ImportError:
        pass
    except Exception as e:
        print(f"[TRANSLATE] OpenVINO load failed: {e}. Falling back to PyTorch.")

    # === TRY 3: PyTorch (Slowest) ===
    import torch
    torch.set_num_threads(4)
    from transformers import MarianMTModel, MarianTokenizer
    
    print("[TRANSLATE] Using Standard PyTorch Models (Slower loading)...")
    _HE_EN_TOKENIZER = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-tc-big-he-en")
    _HE_EN_MODEL = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-tc-big-he-en")
    _HE_EN_MODEL.eval()
    
    _EN_HE_TOKENIZER = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-he")
    _EN_HE_MODEL = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-he")
    _EN_HE_MODEL.eval()
    _TRANSLATION_ENGINE = "pytorch"
    print(f"[TRANSLATE] Standard models loaded in {time.time()-start:.1f}s")

def translate_he_to_en(text: str) -> str:
    """Translate Hebrew to English."""
    load_translation_models()
    
    if _TRANSLATION_ENGINE == "ctranslate2":
        tokens = _HE_EN_TOKENIZER.convert_ids_to_tokens(_HE_EN_TOKENIZER.encode(text))
        results = _HE_EN_MODEL.translate_batch([tokens])
        return _HE_EN_TOKENIZER.decode(_HE_EN_TOKENIZER.convert_tokens_to_ids(results[0].hypotheses[0]))
    else:
        import torch
        with torch.no_grad():
            inputs = _HE_EN_TOKENIZER(text, return_tensors="pt", padding=True, truncation=True, max_length=200)
            outputs = _HE_EN_MODEL.generate(**inputs, max_new_tokens=200, num_beams=2)
        return _HE_EN_TOKENIZER.decode(outputs[0], skip_special_tokens=True)

def translate_en_to_he(text: str) -> str:
    """Translate English to Hebrew using specialized models."""
    # Use ONLY specialized translation models (Helsinki-NLP/CTranslate2)
    # Qwen is a general LLM and produces mixed-language garbage for translation
    load_translation_models()
    
    if _TRANSLATION_ENGINE == "ctranslate2":
        tokens = _EN_HE_TOKENIZER.convert_ids_to_tokens(_EN_HE_TOKENIZER.encode(text))
        results = _EN_HE_MODEL.translate_batch([tokens])
        return _EN_HE_TOKENIZER.decode(_EN_HE_TOKENIZER.convert_tokens_to_ids(results[0].hypotheses[0]))
    else:
        import torch
        with torch.no_grad():
            inputs = _EN_HE_TOKENIZER(text, return_tensors="pt", padding=True, truncation=True, max_length=200)
            outputs = _EN_HE_MODEL.generate(**inputs, max_new_tokens=200, num_beams=2)
        return _EN_HE_TOKENIZER.decode(outputs[0], skip_special_tokens=True)


def fix_hebrew_rtl(text: str) -> str:
    """
    Fix Hebrew RTL display in Windows terminal.
    Uses python-bidi to properly handle right-to-left text.
    Install with: pip install python-bidi
    """
    if not is_hebrew(text):
        return text
    
    # Try to use python-bidi to visually reverse the string for the terminal
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except ImportError:
        # If library missing, return as is (and maybe print warning once)
        return text
    



# ============================================
# LOGGING UTILITIES
# ============================================

class JarvisLogger:
    """Comprehensive logger for Jarvis operations."""
    
    def __init__(self):
        self.start_time = None
        self.model_type = None
        self.total_requests = 0
        self.total_tool_calls = 0
        self.session_start = datetime.now()
    
    def log(self, category: str, message: str):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [{category}] {message}")
    
    def log_startup(self, model_type: str):
        """Log startup info."""
        self.model_type = model_type
        self.log("STARTUP", f"Session started at {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("STARTUP", f"Model: {model_type.upper()}")
    
    def log_request_start(self, user_input: str):
        """Log start of request processing."""
        self.start_time = time.time()
        self.total_requests += 1
        self.log("REQUEST", f"#{self.total_requests} Processing: '{user_input[:50]}...'")
    
    def log_request_end(self, had_tool: bool, tool_name: str = None):
        """Log end of request with timing."""
        elapsed = time.time() - self.start_time
        if had_tool:
            self.total_tool_calls += 1
            self.log("COMPLETE", f"Tool '{tool_name}' executed in {elapsed:.2f}s")
        else:
            self.log("COMPLETE", f"Response generated in {elapsed:.2f}s")
    
    def log_tool(self, tool_name: str, args: dict):
        """Log tool execution."""
        self.log("TOOL", f"Executing: {tool_name}")
        self.log("TOOL", f"Args: {args}")
    
    def log_error(self, error: str):
        """Log error."""
        self.log("ERROR", f"⚠️ {error}")
    
    def log_session_stats(self):
        """Log session statistics."""
        duration = datetime.now() - self.session_start
        print()
        print("=" * 60)
        self.log("STATS", f"Session duration: {duration}")
        self.log("STATS", f"Total requests: {self.total_requests}")
        self.log("STATS", f"Total tool calls: {self.total_tool_calls}")
        self.log("STATS", f"Model used: {self.model_type}")
        print("=" * 60)


# Global logger
LOGGER = JarvisLogger()


# ============================================
# MODEL SELECTION MENU
# ============================================

def select_model():
    """Interactive model selection at startup."""
    print()
    print("=" * 60)
    print("   JARVIS - Step 1: Choose Platform")
    print("=" * 60)
    print()
    print("   [1] LOCAL  - Phi-4 (OpenVINO)")
    print("       └── Runs on your computer, no internet")
    print()
    print("   [2] CLOUD  - Groq (Llama)")
    print("       └── FAST & FREE - No rate limits!")
    print()
    print("=" * 60)
    
    while True:
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            brain.USE_MODEL = "local"
            LOGGER.log_startup("Phi-4 (Local)")
            return "local", None
        elif choice == "2":
            # Ask which Gemini model
            cloud_model = select_cloud_model()
            brain.USE_MODEL = "cloud"
            brain.CLOUD_MODEL_CHOICE = cloud_model
            return "cloud", cloud_model
        else:
            print("Invalid. Enter 1 or 2.")


def select_cloud_model():
    """Select which Gemini model to use."""
    print()
    print("=" * 60)
    print("   JARVIS - Step 2: Choose Groq Model")
    print("=" * 60)
    print()
    print("   [1] Llama 3.3 70B ⭐")
    print("       └── Smart (Like GPT-4)")
    print()
    print("   [2] Llama 3.1 8B")
    print("       └── FAST (14,400 req/day)")
    print()
    print("=" * 60)
    
    model_names = {
        "1": "Llama 3.3 70B",
        "2": "Llama 3.1 8B"
    }
    
    while True:
        choice = input("\nEnter choice (1, 2, or 3): ").strip()
        
        if choice in ["1", "2"]:
            model_num = int(choice)
            LOGGER.log_startup(model_names[choice] + " (Cloud)")
            return model_num
        else:
            print("Invalid. Enter 1 or 2.")


# ============================================
# MAIN FUNCTION
# ============================================

def main():
    # Hardcoded to Local Model (bypass selection)
    model_type = "local"
    brain.USE_MODEL = "local"
    LOGGER.log_startup("Phi-4 (Local)")
    
    print()
    print("=" * 60)
    print("   JARVIS - Hybrid Manager-Worker Architecture")
    print("=" * 60)
    print()
    
    if model_type == "local":
        print("   Model:   Phi-4 (Local)")
    else:
        model_names = {1: "Llama 3.3 70B", 2: "Llama 3.1 8B"}
        print(f"   Model:   {model_names.get(cloud_model, 'Gemini')} (Cloud)")
    
    print("   Manager: LangGraph (Router)")
    print("   Worker:  Semantic Kernel (Executor)")
    print()
    
    LOGGER.log("INIT", "Building hybrid system...")
    init_start = time.time()
    
    graph = brain.build_graph()
    
    # Preload translation models (fastest user experience)
    print("   [INIT] Preloading Hebrew translation models...")
    load_translation_models()
    
    LOGGER.log("INIT", f"System ready in {time.time() - init_start:.2f}s")
    print()
    
    print("-" * 60)
    print("Commands:")
    print("  - 'open chrome'")
    print("  - 'play music on youtube'")
    print("  - 'how is my computer doing'")
    print("  - 'remember my name is John'")
    print("  - 'what do you know about me'")
    print("  - 'read my screen'")
    print("  - 'reset system' (clear history)")
    print("-" * 60)
    print()
    print("Type 'exit' to quit, 'stats' for session statistics.")
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                LOGGER.log_session_stats()
                print("\nGoodbye!")
                break
            
            if user_input.lower() == "stats":
                LOGGER.log_session_stats()
                continue
            
            # Log request start
            LOGGER.log_request_start(user_input)
            
            # === HEBREW DETECTION LAYER ===
            input_was_hebrew = is_hebrew(user_input)
            processing_input = user_input
            hebrew_shortcut_used = False
            
            if input_was_hebrew:
                # FIRST: Try Hebrew shortcuts on ORIGINAL text before translation
                # This avoids translation errors like "להגביה" → "Reply to"
                from jarvis_layers import check_shortcuts
                # Pass context for "Turn it up" logic
                # Use state dict or None (context tracked internally by layered_process)
                last_act = tool_used if 'tool_used' in locals() else None
                hebrew_tool, hebrew_args = check_shortcuts(user_input, last_action=last_act)
                
                if hebrew_tool:
                    LOGGER.log("TRANSLATE", f"Hebrew shortcut detected: {hebrew_tool}")
                    hebrew_shortcut_used = True
                    # Execute the tool directly without translation
                    try:
                        result = execute_tool(hebrew_tool, hebrew_args)
                        # Generate PERSONALITY response (Butler) instead of "Done"
                        if brain._active_router and brain._active_router.pipeline:
                            # Context context
                            now = datetime.now()
                            ctx = f"Today: {now.strftime('%A')}, {now.strftime('%H:%M')}"
                            prompt = build_response_prompt(hebrew_tool, result, ctx)
                            llm_res = brain._active_router.pipeline.generate(prompt, max_new_tokens=150)
                            response = str(llm_res).strip().strip('"')
                        else:
                            response = f"Done, Sir. {result}"
                    except Exception as e:
                        response = f"Error: {e}"

                    # Translate response to Hebrew and output
                    LOGGER.log("TRANSLATE", "Translating response back to Hebrew...")
                    translate_start = time.time()
                    response = translate_en_to_he(response)
                    LOGGER.log("TRANSLATE", f"EN→HE done ({(time.time()-translate_start)*1000:.0f}ms)")
                    LOGGER.log_request_end(True, hebrew_tool)
                    print()
                    # Native terminal handling - no reversal needed
                    print("Jarvis:", response)
                    print()
                    continue  # Skip rest of processing
                
                # If no Hebrew shortcut, translate as normal
                LOGGER.log("TRANSLATE", "Hebrew detected, translating to English...")
                translate_start = time.time()
                processing_input = translate_he_to_en(user_input)
                LOGGER.log("TRANSLATE", f"HE→EN: '{processing_input}' ({(time.time()-translate_start)*1000:.0f}ms)")
            
            # Create state
            state = create_initial_state()
            state["messages"] = [HumanMessage(content=processing_input)]
            state["original_hebrew"] = input_was_hebrew
            
            # Run graph
            print()
            final_state = graph.invoke(state)
            
            # === Get response ===
            response = ""
            tool_used = None
            
            # Check for tool calls
            tool_calls = final_state.get("tool_calls", [])
            if tool_calls:
                tool_used = tool_calls[0].get("name", "unknown")
            
            # Priority 1: Tool results (if tools were executed)
            tool_results = final_state.get("tool_results", [])
            if tool_results:
                for result in tool_results:
                    if result and result.strip():
                        response = result
                        break
            
            # Priority 2: AI message content (for chat responses)
            if not response:
                messages = final_state.get("messages", [])
                for msg in reversed(messages):
                    if hasattr(msg, "content") and msg.content and msg.content.strip():
                        content = msg.content.strip()
                        if content and not content.startswith("{"):
                            response = content
                            break
            
            # Fallback - Use DYNAMIC personality
            if not response:
                if brain._active_router and brain._active_router.pipeline:
                    # Simple wrapper for the LLM
                    def fallback_invoker(prompt):
                        try:
                            # Use generate directly
                            res = brain._active_router.pipeline.generate(prompt, max_new_tokens=100)
                            return str(res)
                        except:
                            return "I seem to have lost my train of thought, Sir."
                    
                    response = generate_fallback_response(fallback_invoker, processing_input)
                else:
                    response = "I couldn't process that. Please try again."
            
            # Priority 1.5: For confirmation responses, skip translation of "CONFIRM:" prefix
            # (The LLM will generate natural response, translator will handle it)
            if tool_used and "ask_confirmation" in str(tool_used) and input_was_hebrew:
                # Clean up the CONFIRM: prefix if present
                if response.startswith("CONFIRM:"):
                    response = response.replace("CONFIRM:", "").strip()
                # Let the translator handle it naturally - no hardcoding
            
            # === HEBREW OUTPUT TRANSLATION LAYER ===
            if input_was_hebrew:
                LOGGER.log("TRANSLATE", "Translating response back to Hebrew...")
                translate_start = time.time()
                response = translate_en_to_he(response)
                LOGGER.log("TRANSLATE", f"EN→HE done ({(time.time()-translate_start)*1000:.0f}ms)")
            
            # Log completion
            LOGGER.log_request_end(tool_used is not None, tool_used)
            
            print()
            print()
            # Apply RTL fix for Hebrew text in terminal
            # display_response = fix_hebrew_rtl(response) if input_was_hebrew else response
            print("Jarvis:", response)
            print()
            
        except KeyboardInterrupt:
            LOGGER.log_session_stats()
            print("\n\nGoodbye!")
            break
        except Exception as e:
            LOGGER.log_error(str(e))
            import traceback
            traceback.print_exc()
            print()


if __name__ == "__main__":
    main()
