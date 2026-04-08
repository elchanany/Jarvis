"""
Fast Semantic Router for Jarvis (0-Latency Architecture)
======================================================
Architecture:
Layer 1 (Fast Match): Sub-millisecond Regex & Exact Word matching.
Layer 2 (Smart Match): Qwen-0.5B-Instruct running via IPEX/Ollama for 
                       structured JSON classification.

Returns: 
- {"route": "action", "tool": "tool_name", "args": {...}}
OR
- {"route": "chat"} -> send to Brain Model
"""

import json
import re
import time
import requests
from typing import Dict, Any, Optional

# --- CONFIGURATION ---
ROUTER_MODEL_URL = "http://127.0.0.1:11434/api/generate"
ROUTER_MODEL_NAME = "qwen2.5:0.5b"  # Default Ollama tag for the 0.5B instruct

# ==========================================
# LAYER 1: ULTRA-FAST REGEX / EXACT MATCHER
# ==========================================

# Dictionary mapping regex patterns to tools and default args
FAST_COMMANDS = [
    # MEDIA CONTROL
    {
        "pattern": r"^(תפסיק|תעצור|עצור|stop|pause)\b(?!.*(מחקר|לחפש))",
        "tool": "control_media",
        "args": {"action": "pause"}
    },
    {
        "pattern": r"^(תמשיך|תנגן|שחק|play|resume)\b(?!.*(שיר|ספוטיפיי))",
        "tool": "control_media",
        "args": {"action": "play"}
    },
    {
        "pattern": r"^(שיר הבא|next|הבא|תעביר)\b",
        "tool": "control_media",
        "args": {"action": "next"}
    },
    {
        "pattern": r"^(שיר קודם|prev|קודם)\b",
        "tool": "control_media",
        "args": {"action": "previous"}
    },
    {
        "pattern": r"(תעביר|שיר הבא|next song|next|skip)",
        "tool": "control_media",
        "args": {"action": "next"}
    },
    
    # SYSTEM CONTROL
    {
        "pattern": r"(מה השעה|מה שעה|מה השעה כעת|what time is it)\b",
        "tool": "get_time",
        "args": {}
    },
    {
        "pattern": r"(מה התאריך|תאריך של היום|איזה יום היום|what is the date)\b",
        "tool": "get_date",
        "args": {}
    },
    {
        "pattern": r"(כבה את המחשב|תכבה תמחשב|תכבה את המחשב|shutdown pc)\b",
        "tool": "system_ops",
        "args": {"action": "shutdown"}
    },
    {
        "pattern": r"(נעל את המסך|תנעל את המחשב|lock screen)\b",
        "tool": "system_ops",
        "args": {"action": "lock"}
    },
    
    # VOLUME
    {
        "pattern": r"(תגביר|תגביר קצת|ווליום למעלה|volume up|louder|increase the volume|increase volume)",
        "tool": "control_volume",
        "args": {"action": "up"}
    },
    {
        "pattern": r"(תחליש|תחליש קצת|ווליום למטה|volume down|quieter|decrease the volume)",
        "tool": "control_volume",
        "args": {"action": "down"}
    },
    {
        "pattern": r"(השתק|תשתיק|mute( the)?( music| volume)?)\b",
        "tool": "control_volume",
        "args": {"action": "mute"}
    },
    {
        "pattern": r"(פתח|תפתח|open|launch)\s+(chrome|spotify|notepad|calculator|settings)",
        "tool": "open_app",
        "args_mapper": lambda match: {"app": match.group(2)}
    },
    {
        "pattern": r"(תנגן|נגן|שיר|play|תדליק שיר)\s+(את\s+)?(.+)",
        "tool": "play_song",
        "args_mapper": lambda match: {"song": match.group(3), "platform": "spotify"}
    },
    {
        "pattern": r"(תוריד את כל החלונות|נקה מסך|show the desktop|show desktop|minimize all)",
        "tool": "window_manager",
        "args": {"action": "minimize_all"}
    },
    {
        "pattern": r"(תסגור את החלון|close this window|close app)",
        "tool": "window_manager",
        "args": {"action": "close_current"}
    },
    {
        "pattern": r"(תגלול למטה|רד למטה|scroll down)",
        "tool": "mouse_keyboard",
        "args": {"action": "scroll_down"}
    },
    {
        "pattern": r"(תגלול למעלה|עלה למעלה|scroll up)",
        "tool": "mouse_keyboard",
        "args": {"action": "scroll_up"}
    },
    {
        "pattern": r"(איך המערכת|מצב מערכת|system health|how is the system doing)",
        "tool": "system_health",
        "args": {}
    },
    {
        "pattern": r"(increase the brightness|brightness|בהירות)",
        "tool": "set_brightness",
        "args": {"level": 100}
    }
]

def layer1_fast_match(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Check if the user input strictly matches a known fast command.
    Latency: ~0.1ms
    """
    text_clean = user_input.lower().strip()
    
    for cmd in FAST_COMMANDS:
        match = re.search(cmd["pattern"], text_clean)
        if match:
            # Check if dynamic args are required
            args = cmd.get("args", {})
            if "args_mapper" in cmd:
                args = cmd["args_mapper"](match)
                
            return {
                "route": "action",
                "tool": cmd["tool"],
                "args": args
            }
    
    return None

# ==========================================
# LAYER 2: QWEN 0.5B SMART ROUTER
# ==========================================

# Minimal system prompt enforcing JSON.
ROUTER_SYSTEM_PROMPT = """You are a Semantic Router for Jarvis.
Your ONLY job is to classify the user's input into one of two categories: 'command' or 'chat'.

1. If the user is asking you to PERFORM A SYSTEM ACTION, output 'command' and pick the exact tool name from this allowed list ONLY:
   - "control_media" (args: {"action": "play" | "pause" | "next" | "previous"})
   - "control_volume" (args: {"action": "up" | "down" | "mute"})
   - "open_app" (args: {"app": "chrome" | "spotify" | "calculator" | "notepad"})
   - "get_time" (args: {})
   - "get_date" (args: {})
   - "search_web" (args: {"query": "<search terms>"})
   - "play_song" (args: {"song": "<song title>", "platform": "spotify"})
   - "set_brightness" (args: {"level": <int 0-100>})
   - "window_manager" (args: {"action": "minimize_all" | "close_current"})
   - "system_health" (args: {})
   - "mouse_keyboard" (args: {"action": "scroll_down" | "scroll_up" | "enter"})

CRITICAL RULE: If the user asks for a physical/system action that is NOT strictly on this list (for example: "turn on lights", "open the door"), YOU MUST output 'chat' with intent 'none'. Do NOT guess or hallucinate a tool.

2. If the user is just conversing, chatting, or asking a complex question, output 'chat'.

You MUST output ONLY valid JSON format. Do not add any text before or after the JSON.
Format:
{
  "type": "command" | "chat",
  "intent": "<exact_tool_name_or_none>",
  "args": {<arguments>}
}

Example 1:
User: "תדליק לי שיר"
{"type": "command", "intent": "play_song", "args": {"song": "", "platform": "spotify"}}

Example 2:
User: "המסך חשוך, תגביר בהירות"
{"type": "chat", "intent": "none", "args": {}}

Example 3:
User: "איך היה היום שלך?"
{"type": "chat", "intent": "none", "args": {}}
"""
def layer2_smart_match(user_input: str) -> Dict[str, Any]:
    """
    Send to Ollama Qwen 0.5B for JSON classification.
    Latency: ~50-100ms
    """
    try:
        payload = {
            "model": ROUTER_MODEL_NAME,
            "prompt": f"{ROUTER_SYSTEM_PROMPT}\n\nUser: \"{user_input}\"\n",
            "stream": False,
            "format": "json"  # Ollama 0.1.26+ supports guaranteed JSON output
        }
        
        response = requests.post(ROUTER_MODEL_URL, json=payload, timeout=5.0)
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "{}")
            
            try:
                data = json.loads(response_text)
                if data.get("type") == "command":
                    return {
                        "route": "action",
                        "tool": data.get("intent"),
                        "args": data.get("args", {})
                    }
                else:
                    return {"route": "chat"}
            except json.JSONDecodeError:
                print(f"[ROUTER L2] Invalid JSON from Qwen 0.5B: {response_text}")
                return {"route": "chat"}
        else:
            print(f"[ROUTER L2] Ollama API Error: {response.status_code}")
            return {"route": "chat"}
            
    except requests.exceptions.RequestException as e:
        print(f"[ROUTER L2] Connection Error to Qwen Router: {e}")
        # If the local router is down, safely fallback to the main brain
        return {"route": "chat"}

# ==========================================
# MAIN ROUTER ENTRY POINT
# ==========================================

def decide_route(user_input: str) -> Dict[str, Any]:
    """
    Main entry point for the zero-latency router.
    Returns standard dict: {"route": "action" | "chat", "tool": "...", "args": {...}}
    """
    print(f"\n[ROUTER] Processing: '{user_input}'")
    
    # 1. Try Fast Match (Layer 1)
    start_time = time.time()
    l1_result = layer1_fast_match(user_input)
    l1_latency = (time.time() - start_time) * 1000
    
    if l1_result:
        print(f"[ROUTER] ⚡ Layer 1 Match! ({l1_latency:.2f}ms) -> {l1_result['tool']}")
        return l1_result
        
    print(f"[ROUTER] ⏭️ Layer 1 Miss ({l1_latency:.2f}ms). Falling back to Layer 2 (Qwen 0.5B)...")
    
    # 2. Try Smart Match (Layer 2)
    start_time = time.time()
    l2_result = layer2_smart_match(user_input)
    l2_latency = (time.time() - start_time) * 1000
    
    if l2_result.get("route") == "action":
        print(f"[ROUTER] 🧠 Layer 2 Command Deteced! ({l2_latency:.2f}ms) -> {l2_result.get('tool')}")
    else:
        print(f"[ROUTER] 💬 Layer 2 Chat Detected! ({l2_latency:.2f}ms). Passing to Main Brain.")
        
    return l2_result

if __name__ == "__main__":
    # Test script locally
    print("Testing Semantic Router...")
    
    test_queries = [
        "תפסיק לאלתר",
        "מה השעה כעת",
        "תגביר",
        "תפתח spotify",
        "נגן שיר של עומר אדם",
        "איך אני מכין פסטה",
    ]
    
    for q in test_queries:
        res = decide_route(q)
        print(f"Result for '{q}': {res}")
        print("-" * 50)
