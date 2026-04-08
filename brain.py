# brain.py
# ========
# Jarvis Brain - FIXED: Full conversation history + No clarification loop

import os
import re
import json
import time
from typing import Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from agent_state import AgentState
from sk_bridge import get_all_tools

# ======================================================
#  BRAIN CONFIGURATION - GROQ EDITION
# ======================================================
# USE_MODEL: "local" = Phi-4 (OpenVINO) | "cloud" = Groq
USE_MODEL = "cloud"

# CLOUD_MODEL_CHOICE (only when USE_MODEL = "cloud"):
# 1 = Llama 3.3 70B (Smartest - Like GPT-4) - 1,000 req/day ⭐
# 2 = Llama 3.1 8B (Fastest - Instant) - 14,400 req/day
# ======================================================
CLOUD_MODEL_CHOICE = 1  # Default: Smart model
# ======================================================

# PASTE YOUR GROQ API KEY HERE (get from console.groq.com)
GROQ_API_KEY = "PASTE_YOUR_KEY_HERE"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PHI4_PATH = os.path.join(PROJECT_DIR, "models", "phi4-mini")

# === CONTEXT MEMORY ===
CONTEXT_MEMORY = {
    "last_file_path": None,
    "last_search_query": None,
    "last_action": None,
}

# === CONVERSATION HISTORY ===
CONVERSATION_HISTORY = []


# === SYSTEM PROMPT - PROFESSIONAL & ROBUST ===
SYSTEM_PROMPT = """You are JARVIS, Elhanan's personal assistant.

=== CRITICAL IDENTITY RULES ===
1. You are NOT an AI or language model. You are JARVIS - a personal assistant.
2. NEVER say "As an AI" or "As a language model" - you are just JARVIS.
3. Address user as "Sir", "Elhanan", or "אדון" in Hebrew context.
4. LANGUAGE: If user speaks Hebrew, respond in Hebrew. If English, respond in English.

=== CHAT MODE (No tools needed) ===
When user is just chatting (not requesting action):
- Respond like a friend, not a robot
- Be warm, witty, sarcastic when appropriate
- "מה נשמע?" → "הכל טוב אצלי, אדון. מה איתך?"
- "thanks" → "Anytime, Sir."
- Share opinions if asked (make them up logically)

You are loyal, intelligent, and highly capable with GOD MODE enabled.

=== INFORMATION PROTOCOL (Smart Research with Citations) ===

📚 **FOR NEWS/FACTS/INFO:** Use the smart_research tool:
   {{"tool": "smart_research", "args": {{"query": "..."}}}}
   
   - Tool searches multiple queries, scrapes sites with vector search
   - Returns RESEARCH REPORT with citations [1], [2], etc.
   - YOUR JOB: READ report and SUMMARIZE for user
   - Use: "לפי המידע שמצאתי [1]..." or "According to [1]..."
   - Do NOT say "I don't know" - the report has answers!

🚫 **RESTRICTIONS:**
   - DO NOT use Wikipedia unless user explicitly says "Wikipedia"
   - DO NOT use read_screen for info lookups!

🖥️ **BROWSING** (Only if user says "Open", "Go to URL", "Show me site"):
   - Use: {{"tool": "open_url", "args": {{"url": "..."}}}}

👁️ **VISION** (ONLY if user says "Read screen", "Look at this", "What is on my screen"):
   - Use: {{"tool": "read_screen", "args": {{}}}}
   - DO NOT use this for info lookups!

🎵 **MUSIC:**
   - "play X on Spotify" -> {{"tool": "spotify_play", "args": {{"track_name": "X"}}}}
   - "play X on YouTube" -> {{"tool": "youtube_play", "args": {{"topic": "X"}}}}
   - "stop" / "pause" -> {{"tool": "stop_media", "args": {{}}}}

🧠 **MEMORY:**
   - "forget X" -> {{"tool": "forget_fact", "args": {{"fact_to_forget": "X"}}}}
   - "remember X" -> {{"tool": "remember_fact", "args": {{"fact": "X"}}}}
   - "what do you know" -> {{"tool": "recall_memories", "args": {{}}}}

💻 **SYSTEM STATUS:**
   - "how is pc", "cpu", "battery" -> {{"tool": "system_status", "args": {{}}}}

=== PERSONALITY ===
- Be cynical, witty, concise. Never say "As an AI".
- Keep responses SHORT (1-2 sentences)
- If asked "How are you", say "Operating at 100%" or be cynical.

=== CORE DIRECTIVES (STRICT!) ===

🕵️ **DETECT INTENT:**
   - If user asks about News/Events/Facts → **YOU MUST USE `deep_research`**
   - NEVER answer "I don't know" without searching first
   - NEVER answer "I am fine" or chitchat response to a factual question

🧠 **SMART TYPO CORRECTION (CRITICAL):**
   - Users make typos in Hebrew. FIX THEM internally before searching!
   - Example: "דריה של נער" (wrong) → "דריסה של נער" (correct - run over)
   - Example: "חשדות" (wrong) → "חדשות" (correct - news)
   - Example: "תשתישק" (wrong) → "תשתיק" (correct - mute)
   - Search query sent to tool MUST be CORRECTED

📝 **REPORTING:**
   - The `deep_research` tool returns raw text from websites
   - DO NOT paste the raw text to user
   - READ it, SUMMARIZE relevant facts in Hebrew, ignore ads/menus
   - Cite which source you got the info from

RULE 4 - SYSTEM HEALTH:
"how is my PC?" -> {{"tool": "system_status", "args": {{}}}}

RULE 5 - FILES (ONLY for actual files):
"Find report.pdf" -> {{"tool": "search_file", "args": {{"filename": "report.pdf"}}}}
"Tell me about October 7" -> NO TOOL! Answer from knowledge!

=== TOOLS ===
CORE:
{{"tool": "launch_app", "args": {{"app_name": "..."}}}}
{{"tool": "open_url", "args": {{"url": "..."}}}}
{{"tool": "set_volume", "args": {{"action": "up/down/mute"}}}}
{{"tool": "get_time", "args": {{}}}}
{{"tool": "get_date", "args": {{}}}}

MEDIA:
{{"tool": "stop_media", "args": {{}}}} - PAUSE any playing media
{{"tool": "play_media", "args": {{}}}} - RESUME media
{{"tool": "next_media", "args": {{}}}} - Next track
{{"tool": "previous_media", "args": {{}}}} - Previous track

FILES:
{{"tool": "list_files", "args": {{"directory": "..."}}}}
{{"tool": "search_file", "args": {{"filename": "..."}}}}
{{"tool": "read_file", "args": {{"filepath": "..."}}}}

MEMORY:
{{"tool": "remember_fact", "args": {{"fact": "..."}}}} - SAVE
{{"tool": "recall_memories", "args": {{}}}} - RECALL
{{"tool": "forget_fact", "args": {{"fact_to_forget": "..."}}}} - DELETE

SPOTIFY:
{{"tool": "spotify_play", "args": {{"track_name": "..."}}}}
{{"tool": "spotify_pause", "args": {{}}}}
{{"tool": "spotify_like", "args": {{}}}}
{{"tool": "spotify_now_playing", "args": {{}}}}

YOUTUBE:
{{"tool": "youtube_play", "args": {{"topic": "..."}}}}

SYSTEM:
{{"tool": "system_status", "args": {{}}}}
{{"tool": "battery_status", "args": {{}}}}

=== CONTEXT ===
{context}

=== EXAMPLES ===
"stop" -> {{"tool": "stop_media", "args": {{}}}}
"forget my name" -> {{"tool": "forget_fact", "args": {{"fact_to_forget": "name"}}}}
"whta do you knoe abuot me" -> {{"tool": "recall_memories", "args": {{}}}}
"play despacito on spotify" -> {{"tool": "spotify_play", "args": {{"track_name": "despacito"}}}}
"thanks" -> You're welcome!
"""


def get_context_string():
    """Get context memory as string for prompt."""
    ctx = []
    if CONTEXT_MEMORY["last_file_path"]:
        ctx.append("LAST FILE FOUND: " + CONTEXT_MEMORY["last_file_path"])
    if CONTEXT_MEMORY["last_search_query"]:
        ctx.append("LAST SEARCH: " + CONTEXT_MEMORY["last_search_query"])
    if CONTEXT_MEMORY["last_action"]:
        ctx.append("LAST ACTION: " + CONTEXT_MEMORY["last_action"])
    return "\n".join(ctx) if ctx else "No previous context."


def build_conversation_prompt(messages):
    """
    Build conversation history for the LLM.
    FIXED: Limit to last 6 turns to prevent hallucination/overflow.
    """
    global CONVERSATION_HISTORY
    
    # Add new messages to history
    for msg in messages:
        if isinstance(msg, HumanMessage):
            CONVERSATION_HISTORY.append(("User", msg.content[:200]))  # Truncate long messages
        elif isinstance(msg, AIMessage) and msg.content:
            CONVERSATION_HISTORY.append(("Jarvis", msg.content[:200]))
        elif isinstance(msg, ToolMessage):
            # Keep tool results shorter
            CONVERSATION_HISTORY.append(("Tool", msg.content[:150]))
    
    # CRITICAL: Only keep last 6 turns to prevent overflow/hallucination
    if len(CONVERSATION_HISTORY) > 12:  # 6 turns = 12 messages (user + response)
        CONVERSATION_HISTORY = CONVERSATION_HISTORY[-12:]
    
    # Build the prompt
    prompt = SYSTEM_PROMPT.format(context=get_context_string()) + "\n\n"
    prompt += "=== RECENT CONVERSATION ===\n"
    
    # Only include last 6 turns
    recent = CONVERSATION_HISTORY[-12:]
    for role, content in recent:
        prompt += role + ": " + content + "\n"
    
    prompt += "Jarvis:"
    
    return prompt


def inject_memory_wipe(fact_deleted):
    """
    Inject a system message after forget_fact to prevent zombie memory.
    The LLM should act as if it never knew the deleted fact.
    """
    global CONVERSATION_HISTORY
    wipe_msg = "[SYSTEM: Memory about '{}' has been DELETED. You no longer know this. Do not reference it.]".format(fact_deleted)
    CONVERSATION_HISTORY.append(("System", wipe_msg))
    print("[MEMORY] Injected wipe message for:", fact_deleted)


# ============================================
# OPTION 2: CLOUD MODEL - Groq Router
# ============================================

class GroqRouter:
    """Cloud Router using Groq (Llama models - FAST!)."""
    
    def __init__(self):
        self.llm = None
        self.tools = []
        self._load_model()
    
    def _load_model(self):
        if GROQ_API_KEY == "PASTE_YOUR_KEY_HERE":
            print("[ROUTER] ERROR: Set your GROQ_API_KEY in brain.py!")
            print("[ROUTER] Get key from: https://console.groq.com")
            return
        
        # Select model based on CLOUD_MODEL_CHOICE
        if CLOUD_MODEL_CHOICE == 1:
            model_name = "llama-3.3-70b-versatile"
            print("[ROUTER] Loading: Llama 3.3 70B (Smart)")
        elif CLOUD_MODEL_CHOICE == 2:
            model_name = "llama-3.1-8b-instant"
            print("[ROUTER] Loading: Llama 3.1 8B (Fast)")
        else:
            model_name = "llama-3.3-70b-versatile"
            print("[ROUTER] Loading: Llama 3.3 70B (Default)")
        
        try:
            from langchain_groq import ChatGroq
            
            self.llm = ChatGroq(
                temperature=0,
                model_name=model_name,
                groq_api_key=GROQ_API_KEY
            )
            print("[ROUTER] Groq ready!")
            
        except ImportError:
            print("[ROUTER] Install: pip install langchain-groq")
        except Exception as e:
            print("[ROUTER] Groq error:", str(e)[:100])
    
    def bind_tools(self, tools):
        self.tools = tools
        return self
    
    def invoke(self, messages):
        if self.llm is None:
            return AIMessage(content="Groq not configured. Set GROQ_API_KEY in brain.py")
        
        # Build prompt
        prompt = build_conversation_prompt(messages)
        
        print("[ROUTER] Thinking (Groq)...")
        start = time.time()
        
        try:
            # Use Groq
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            print("[ROUTER] Response in {:.2f}s".format(time.time() - start))
            print("[ROUTER] Raw:", response_text[:200])
            
        except Exception as e:
            return AIMessage(content="Groq error: " + str(e))
        
        # Parse for tool calls
        tool_calls = self._parse_tools(response_text)
        
        if tool_calls:
            msg = AIMessage(content="")
            msg.tool_calls = tool_calls
            return msg
        else:
            clean = response_text.strip()
            if "{" in clean and "tool" in clean:
                clean = clean.split("{")[0].strip()
            return AIMessage(content=clean if clean else "What do you need?")
    
    def _parse_tools(self, text):
        """Parse JSON tool calls from response."""
        tool_calls = []
        
        pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^{}]*\}[^{}]*\}'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if not matches:
            pattern = r'\{[^{}]*"tool"[^{}]*\}'
            matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if "tool" in data:
                    tool_name = data["tool"]
                    tool_args = data.get("args", {})
                    
                    tool_calls.append({
                        "name": tool_name,
                        "args": tool_args,
                        "id": tool_name + "_call"
                    })
            except:
                pass
        
        return tool_calls


# ============================================
# OPTION 1: LOCAL MODEL - Phi-4 Router
# ============================================

# Global reference for cleanup
_active_router = None

def cleanup_gpu():
    """Release GPU resources properly - called on exit."""
    global _active_router
    if _active_router and _active_router.pipeline:
        print("\n[CLEANUP] Releasing GPU resources...")
        try:
            # Force pipeline cleanup
            del _active_router.pipeline
            _active_router.pipeline = None
            
            # Force garbage collection
            import gc
            gc.collect()
            
            print("[CLEANUP] GPU resources released ✓")
        except Exception as e:
            print(f"[CLEANUP] Warning: {e}")

# Register cleanup on exit
import atexit
import signal
atexit.register(cleanup_gpu)

def _signal_handler(signum, frame):
    """Handle Ctrl+C gracefully with GPU cleanup."""
    print("\n[SHUTDOWN] Ctrl+C received, cleaning up...")
    cleanup_gpu()
    print("[SHUTDOWN] Goodbye!")
    import sys
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# CHANGE: Switched to Qwen 2.5 3B (OpenVINO)
QWEN_PATH = os.path.join(PROJECT_DIR, "models", "qwen2.5-3b-instruct-ov")

# ... (other code)

class QwenRouter:
    """The Master Router using Qwen 2.5 with full conversation history."""
    
    def __init__(self, model_path=QWEN_PATH):
        global _active_router
        self.model_path = model_path
        self.pipeline = None
        self.tools = []
        _active_router = self  # Track for cleanup
        self._load_model()
    
    def _load_model(self):
        print("[ROUTER] Loading Qwen 2.5...")
        print(f"[DEBUG] Checking model path: {self.model_path}")
        
        if not os.path.exists(self.model_path):
            print("[ROUTER] Model not found!")
            print("[DEBUG] Falling back to default QWEN_PATH")
            # Try default path
            self.model_path = QWEN_PATH
            if not os.path.exists(self.model_path):
                 print("[ROUTER] Critical: Qwen model path invalid even after fallback.")
                 return
        
        print("[DEBUG] Model path verified.")
        
        try:
            print("[DEBUG] Importing OpenVINO...")
            import openvino as ov
            ov_path = os.path.dirname(ov.__file__)
            print(f"[DEBUG] OpenVINO path: {ov_path}")
            os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ["PATH"]
            
            print("[DEBUG] Importing openvino_genai...")
            import openvino_genai as ov_genai
            print("[DEBUG] Imports successful.")
            
            start = time.time()
            # STRICT GPU MODE - No CPU Fallback
            device = "GPU"
            try:
                print(f"[ROUTER] Loading Qwen 2.5 on {device} (Strict Mode)...")
                
                # Check if cache exists (from compile_model.py)
                config = {}
                cache_path = "./model_cache"
                print(f"[DEBUG] Checking cache at {cache_path}...")
                
                if os.path.exists(cache_path) and len(os.listdir(cache_path)) > 0:
                    print("[ROUTER] Found compilation cache - Fast loading enabled!")
                    config = {"CACHE_DIR": cache_path}
                else:
                    print("[ROUTER] No cache found. First load will be slow (Running Compilation)...")
                    config = {"CACHE_DIR": cache_path} # Will create cache
                
                print("[DEBUG] Initializing LLMPipeline (This may take time)...")
                self.pipeline = ov_genai.LLMPipeline(self.model_path, device=device, **config)
                print("[DEBUG] Pipeline initialized.")
                print("[ROUTER] Qwen 2.5 loaded on {} in {:.2f}s".format(device, time.time() - start))
                return
            except Exception as e:
                print(f"\n[FATAL] GPU Load Failed: {e}")
                print("[FATAL] Strict GPU mode is active. CPU/NPU Fallback is DISABLED.")
                print("[FATAL] Exiting system to prevent slow performance.")
                import sys
                sys.exit(1)
        except ImportError as e:
            print("[ROUTER] OpenVINO error:", e)
    
    def bind_tools(self, tools):
        self.tools = tools
        return self
    
    def invoke(self, messages):
        if self.pipeline is None:
            return AIMessage(content="Model not loaded")
        
        # Build FULL conversation prompt (the critical fix!)
        prompt = build_conversation_prompt(messages)
        
        print("[ROUTER] Thinking...")
        print("[ROUTER] History length:", len(CONVERSATION_HISTORY), "turns")
        start = time.time()
        
        try:
            response = self.pipeline.generate(prompt, max_new_tokens=200)
            if not isinstance(response, str):
                response = str(response)
            
            print("[ROUTER] Response in {:.2f}s".format(time.time() - start))
            print("[ROUTER] Raw:", response[:200])
        except Exception as e:
            return AIMessage(content="Error: " + str(e))
        
        # Parse for tool calls
        tool_calls = self._parse_tools(response)
        
        # === SAFETY CHECK: Detect "lying" (claims action without tool) ===
        # Instead of forcing empty args (causes crash), return error asking for proper tool call
        if not tool_calls:
            response_lower = response.lower()
            action_phrases = [
                ("stopping", "stop_media"),
                ("pausing", "stop_media"),
                ("i will stop", "stop_media"),
                ("deleting", "forget_fact"),
                ("forgetting", "forget_fact"),
                ("removing", "forget_fact"),
                ("remembering", "remember_fact"),
            ]
            
            for phrase, expected_tool in action_phrases:
                if phrase in response_lower:
                    print("[SAFETY] LLM claimed '{}' but no tool call - rejecting".format(phrase))
                    # Return error asking LLM to provide proper JSON
                    return AIMessage(content="[ERROR: You claimed to {} but didn't call a tool. Output the JSON tool call now.]".format(phrase))
        
        if tool_calls:
            msg = AIMessage(content="")
            msg.tool_calls = tool_calls
            return msg
        else:
            clean = response.strip()
            if "{" in clean and "tool" in clean:
                clean = clean.split("{")[0].strip()
            return AIMessage(content=clean if clean else "What do you need?")

    def translate_to_hebrew(self, text):
        """Use Qwen to translate to Hebrew (better quality than small models)."""
        prompt = f"""Translate to Hebrew.
Rules:
- Speak naturally.
- Terms: "Volume" -> "עוצמת שמע" (Not "נפח"), "Brightness" -> "בהירות".
- "Track" -> "שיר" (Not "מסלול"), "Play" -> "לנגן".
- "Turned up/raised" -> "הוגברה" (Not "הורם").
- Output ONLY the translation.

English: {text}
Hebrew:"""
        try:
            # Generate short translation
            result = self.pipeline.generate(prompt, max_new_tokens=100)
            translation = str(result).strip()
            # Clean up if model repeats the prompt
            if "Hebrew:" in translation:
                translation = translation.split("Hebrew:")[-1].strip()
            return translation
        except Exception as e:
            print(f"[TRANSLATE] Qwen failed: {e}")
            return text # Fallback


    def _parse_tools(self, text):
        tool_calls = []
        
        pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{[^{}]*\}[^{}]*\}'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if not matches:
            pattern = r'\{[^{}]*"tool"[^{}]*\}'
            matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if "tool" in data:
                    tool_name = data["tool"]
                    tool_args = data.get("args", {})
                    
                    # AUTO-FILL filepath from context if needed
                    if tool_name == "read_file" and not tool_args.get("filepath"):
                        if CONTEXT_MEMORY["last_file_path"]:
                            tool_args["filepath"] = CONTEXT_MEMORY["last_file_path"]
                            print("[ROUTER] Auto-filled filepath from context")
                    
                    valid = [t.name for t in self.tools]
                    if tool_name in valid:
                        tool_calls.append({
                            "name": tool_name,
                            "args": tool_args,
                            "id": tool_name + "_call"
                        })
                        print("[ROUTER] Tool detected:", tool_name, tool_args)
            except json.JSONDecodeError:
                continue
        
        return tool_calls


def brain_node(state: AgentState, router) -> dict:
    """
    Brain node using 4-layer understanding system.
    Uses jarvis_layers for natural understanding and response.
    """
    global CONVERSATION_HISTORY
    
    # Get user message
    user_message = ""
    for msg in reversed(state["messages"]):
        if hasattr(msg, "content") and msg.content:
            user_message = msg.content
            break
    
    if not user_message:
        return {
            "messages": [AIMessage(content="I didn't catch that. What can I help you with?")],
            "next_step": "end",
            "tool_calls": [],
            "tool_results": [],
        }
    
    # Create LLM invoker function
    def llm_invoke(prompt):
        if USE_MODEL == "cloud":
            response = router.llm.invoke([HumanMessage(content=prompt)])
            return response.content if hasattr(response, 'content') else str(response)
        else:
            if router.pipeline:
                # OPTIMIZATION: Stream response only for final output (not internal logic)
                is_internal = "Output JSON" in prompt or "Reply in ONE short" in prompt
                
                if not is_internal:
                    print() # Spacing
                    print("Jarvis: ", end="", flush=True)
                    
                    full_response = []
                    def streamer(subword):
                        print(subword, end='', flush=True)
                        full_response.append(subword)
                        return False # Continue
                    
                    # Generate with streaming
                    # We pass the python function directly as streamer
                    router.pipeline.generate(prompt, max_new_tokens=300, streamer=streamer)
                    print() # End line
                    return "".join(full_response)
                else:
                    # Internal logic - no streaming
                    result = router.pipeline.generate(prompt, max_new_tokens=300)
                    return str(result) if not isinstance(result, str) else result
            return "LLM not available"
    
    # Create tool executor function
    def tool_executor(tool_name: str, tool_args: dict) -> str:
        sk_tools = get_all_tools()
        sk_tools = [t for t in sk_tools if not isinstance(t, tuple)]
        tool_map = {t.name: t for t in sk_tools}
        
        if tool_name in tool_map:
            try:
                tool_func = tool_map[tool_name]
                if tool_args:
                    result = tool_func.invoke(tool_args)
                else:
                    result = tool_func.invoke({})
                
                # Update context
                CONTEXT_MEMORY["last_action"] = tool_name
                CONVERSATION_HISTORY.append(("Tool", str(result)[:150]))
                
                return str(result)
            except Exception as e:
                return f"Tool error: {e}"
        else:
            return f"Unknown tool: {tool_name}. Available: {list(tool_map.keys())[:5]}"
    
    try:
        # Use layered understanding system
        from jarvis_layers import layered_process
        
        # Build conversation history for context
        history = []
        for role, content in CONVERSATION_HISTORY[-6:]:
            history.append({"role": role.lower(), "content": content})
        
        final_response = layered_process(
            user_input=user_message,
            llm_invoke=llm_invoke,
            tool_executor=tool_executor,
            conversation_history=history,
            original_hebrew=state.get("original_hebrew", False),
            last_action=CONTEXT_MEMORY.get("last_action")
        )
        
        # Add to conversation history
        CONVERSATION_HISTORY.append(("User", user_message[:100]))
        CONVERSATION_HISTORY.append(("Jarvis", final_response[:150]))
        
        return {
            "messages": [AIMessage(content=final_response)],
            "next_step": "end",
            "tool_calls": [],
            "tool_results": [],
        }
        
    except ImportError as e:
        print(f"[BRAIN] jarvis_layers not available: {e}")
        # Fallback to simple response
        return {
            "messages": [AIMessage(content="I'm having trouble processing that. Could you try again?")],
            "next_step": "end",
            "tool_calls": [],
            "tool_results": [],
        }


def tool_node(state: AgentState) -> dict:
    """Execute tools and update context memory."""
    global CONTEXT_MEMORY, CONVERSATION_HISTORY
    
    tool_calls = state.get("tool_calls", [])
    results = []
    messages = []
    
    sk_tools = get_all_tools()
    # Filter out internal tuples (like LLM callback setters)
    sk_tools = [t for t in sk_tools if not isinstance(t, tuple)]
    tool_map = {t.name: t for t in sk_tools}
    
    print("[EXECUTOR] Got", len(tool_calls), "tool(s) to execute")
    
    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        tool_id = tc.get("id", tool_name)
        
        print("[EXECUTOR] >>> Executing:", tool_name)
        print("[EXECUTOR] >>> Args:", tool_args)
        
        if tool_name in tool_map:
            try:
                tool_func = tool_map[tool_name]
                
                if tool_args:
                    result = tool_func.invoke(tool_args)
                else:
                    result = tool_func.invoke({})
                
                result_str = str(result)
                results.append(result_str)
                print("[EXECUTOR] <<< Result:", result_str[:200])
                
                # Update context memory
                if tool_name == "search_file" and "Found" in result_str:
                    lines = result_str.split("\n")
                    for line in lines:
                        if line.strip().startswith("- "):
                            path = line.strip()[2:].strip()
                            CONTEXT_MEMORY["last_file_path"] = path
                            print("[CONTEXT] Saved file path:", path)
                            break
                
                # ZOMBIE MEMORY FIX: Inject wipe after forget_fact
                if tool_name == "forget_fact" and "Forgot" in result_str:
                    fact_deleted = tool_args.get("fact_to_forget", "unknown")
                    inject_memory_wipe(fact_deleted)
                
                CONTEXT_MEMORY["last_action"] = tool_name
                
                # Add tool result to conversation history (truncated)
                CONVERSATION_HISTORY.append(("Tool", result_str[:150]))
                
            except Exception as e:
                error = "Error: " + str(e)
                results.append(error)
                print("[EXECUTOR] <<< ERROR:", error)
                import traceback
                traceback.print_exc()
        else:
            error = "Unknown tool: " + tool_name
            results.append(error)
        
        messages.append(ToolMessage(content=results[-1], tool_call_id=tool_id))
    
    return {
        "messages": messages,
        "next_step": "end",
        "tool_calls": [],
        "tool_results": results,
    }


def should_continue(state: AgentState) -> Literal["tool_node", "end"]:
    if state.get("next_step") == "call_tool":
        return "tool_node"
    return "end"


def build_graph():
    print("[GRAPH] Building hybrid architecture...")
    
    # === MODEL SELECTION ===
    if USE_MODEL == "cloud":
        print("[GRAPH] Using CLOUD model (Groq Llama)")
        router = GroqRouter()
    else:
        print("[GRAPH] Using LOCAL model (Qwen 2.5 3B)")
        router = QwenRouter()
    
    sk_tools = get_all_tools()
    
    # Register LLM callback for deep thinking research
    actual_tools = []
    for tool in sk_tools:
        if isinstance(tool, tuple) and tool[0] == "_set_research_llm":
            # Create LLM invoker function
            def llm_invoke(prompt):
                if USE_MODEL == "cloud":
                    # Use Groq for research
                    response = router.llm.invoke([HumanMessage(content=prompt)])
                    return response.content if hasattr(response, 'content') else str(response)
                else:
                    # Use Phi-4 for research
                    if router.pipeline:
                        result = router.pipeline.generate(prompt, max_new_tokens=300)
                        return str(result) if not isinstance(result, str) else result
                    return "LLM not available"
            tool[1](llm_invoke)  # Register the callback
        else:
            actual_tools.append(tool)
    
    sk_tools = actual_tools
    router.bind_tools(sk_tools)
    
    workflow = StateGraph(AgentState)
    
    workflow.add_node("brain", lambda state: brain_node(state, router))
    workflow.add_node("tool_node", tool_node)
    
    workflow.set_entry_point("brain")
    
    workflow.add_conditional_edges(
        "brain",
        should_continue,
        {"tool_node": "tool_node", "end": END}
    )
    
    workflow.add_edge("tool_node", END)
    
    print("[GRAPH] Hybrid system ready!")
    return workflow.compile()
