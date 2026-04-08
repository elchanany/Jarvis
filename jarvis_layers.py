"""
JARVIS Unified Layer System v3
==============================
ONE LLM call returns ALL analysis values.
Then routes to appropriate action.

Flow:
1. Context injection (date/time)
2. Shortcuts (bypass LLM for common patterns)
3. ONE unified LLM call → structured JSON output
4. Route based on category (A/C/M/K)
5. Execute action if needed
6. Generate response
"""

import time
import json
import re
from typing import Callable, Dict, Any, Optional, List
from datetime import datetime


# ============================================
# AVAILABLE TOOLS
# ============================================
TOOLS = {
    "launch_app": "Open app (chrome, spotify, notepad)",
    "open_url": "Open website URL",
    "set_volume": "Volume control (up, down, mute)",
    "get_time": "Get current time",
    "get_date": "Get current date",
    "youtube_play": "Play on YouTube",
    "spotify_play": "Play on Spotify",
    "stop_media": "Stop/pause media",
    "system_status": "PC status (CPU, RAM, battery)",
    "read_screen": "Read screen text (OCR)",
    "remember_fact": "Remember something",
    "recall_memories": "Recall memories",
    "forget_fact": "Forget something",
    "smart_research": "Search web for info",
    "telegram_news": "Read Israeli news",
}


def build_tools_list() -> str:
    """Build compact tools list for prompt."""
    return ", ".join(TOOLS.keys())


# ============================================
# DIRECT SHORTCUTS (Bypass LLM)
# ============================================

# ============================================
# SAFETY & CONFIRMATION STATE
# ============================================
PENDING_ACTION = None
PENDING_ARGS = None

def check_shortcuts(text: str, last_action: str = None) -> tuple:
    """
    Check for direct keyword matches.
    Returns (tool_name, args) or (None, None) if no match.
    Handled Confirmation logic for dangerous actions.
    """
    global PENDING_ACTION, PENDING_ARGS
    
    text_lower = text.lower()

    # ----------------------------------------
    # 0. CONTEXT SHORTCUTS (handle "more", "again", "download more")
    # ----------------------------------------
    # "Download More" is a common bad translation of "תוריד עוד" (Lower more)
    if any(w in text_lower for w in ["download more", "lower more", "reduce more", "decrease more"]):
        if last_action == "set_volume":
             return "set_volume", {"action": "down"}
        if last_action == "set_brightness":
             return "set_brightness", {"level": "-20"}
             
    # "I didn't see/hear" implies action failed or was too weak -> Repeat/Intensify
    if any(w in text_lower for w in ["didn't see", "not see", "didn't hear", "not hear", "לא ראיתי", "לא שמעתי", "לא הרגשתי"]):
        if last_action == "set_volume":
             # If they didn't hear/see change, maybe do it MORE? Or just repeat?
             # Let's repeat but assume same direction as before (needs state, but 'up' is safe guess if complained about not hearing)
             return "set_volume", {"action": "up"} # Default to UP if complaint is "didn't hear"
        if last_action == "set_brightness":
             return "set_brightness", {"level": "+20"}
             
    if any(w in text_lower for w in ["up", "higher", "increase", "more"]):
        if last_action == "set_volume" and len(text_lower.split()) < 4:
             return "set_volume", {"action": "up"}

    # CORRECTION ("I meant Creep")
    # If user corrects a previous media search failure
    if any(w in text_lower for w in ["i meant", "no i meant", "actually i meant", "correction", "התכוונתי", "לא התכוונתי"]):
        if last_action == "spotify_play" or last_action == "youtube_play":
            # Extract the correction term
            # remove "i meant", "no", "actually"
            clean_term = text_lower
            for prefix in ["no i meant", "i meant", "actually", "correction", "no", "התכוונתי ל", "התכוונתי", "לא"]:
                clean_term = clean_term.replace(prefix, "")
            
            clean_term = clean_term.strip()
            if clean_term:
                return last_action, {"track_name" if last_action == "spotify_play" else "topic": clean_term}
    
    # ----------------------------------------
    # 1. HANDLE CONFIRMATION (If pending)
    # ----------------------------------------
    if PENDING_ACTION:
        # Check for YES
        if any(w in text_lower for w in ["yes", "sure", "confirm", "do it", "batuach", "ken", "כן", "בטח", "בטוח", "מאשר"]):
            tool = PENDING_ACTION
            args = PENDING_ARGS
            PENDING_ACTION = None
            PENDING_ARGS = None
            return tool, args
        
        # Check for NO (or implicit cancel if not yes)
        # Use word boundaries to avoid matching "lo" inside "lock"
        cancel_words = ["no", "cancel", "don't", "stop", "לא", "בטל", "אל תעשה"]
        words = text_lower.split()  # Split into words
        if any(w in words for w in cancel_words):
            PENDING_ACTION = None
            PENDING_ARGS = None
            return "ask_confirmation", {"question": "Cancelled. What else can I help with?"}
            
        # If user says something unrelated -> Cancel and process normally? 
        # Or should we be strict? User said "I just want...", so let's allow implicit cancel.
        PENDING_ACTION = None
        PENDING_ARGS = None
        # fallthrough to normal processing
    
    # ----------------------------------------
    # 2. SHORTCUTS
    # ----------------------------------------
    
    # Time/Date/Day - ORDER MATTERS
    if any(w in text_lower for w in ["what time", "time is it", "מה השעה"]):
        return "get_time", {}
    if any(w in text_lower for w in ["what date", "the date", "מה התאריך", "תאריך"]):
        return "get_date", {}
    # Day - catch bad translation "what a day" too
    if any(w in text_lower for w in ["what day is it", "what day", "what a day", "איזה יום היום", "איזה יום"]):
        return "get_day", {}
    
    # MUTE - catch "shut the music" which comes from "תשתיק את המוזיקה"
    if any(w in text_lower for w in ["mute", "shut the music", "shut down the music", "silence", "השתק", "תשתיק"]):
        return "set_volume", {"action": "mute"}
    
    # Brightness - detect intent keywords (Specific > Generic)
    brightness_keywords = ["brightness", "בהירות", "dazzle", "glare", "מסנוור", "תבהיר", "הבהר", "תאורה", "lighting", "המסך"]
    if any(w in text_lower for w in brightness_keywords):
        import re
        # First check for specific number
        match = re.search(r'(\d+)', text_lower)
        if match:
            return "set_brightness", {"level": int(match.group(1))}
        # Check for DOWN/REDUCE first
        if any(w in text_lower for w in ["down", "lower", "reduce", "dim", "decrease", "הנמך", "תנמיך", "הורד", "תוריד", "dark", "dazzle", "glare", "מסנוור", "כהה"]):
            return "set_brightness", {"level": "-20"}
        # Check for UP/INCREASE
        if any(w in text_lower for w in ["up", "increase", "raise", "higher", "הגבר", "תגביר", "העלה", "תעלה", "תגביה"]):
            return "set_brightness", {"level": "+20"}
        # No direction specified - just get current brightness
        return "get_brightness", {}

    # AMBIGUOUS "Turn up/down" - Check Context First
    if any(w in text_lower for w in ["turn up", "boost", "increase", "raise"]):
         if last_action == "set_brightness":
             return "set_brightness", {"level": "+20"}
         # Default to Volume if no specific context
         return "control_volume", {"action": "up"}

    if any(w in text_lower for w in ["turn down", "lower", "reduce", "decrease"]):
         if last_action == "set_brightness":
             return "set_brightness", {"level": "-20"}
         # Default to Volume if no specific context
         return "control_volume", {"action": "down"}

    # Volume - Specific keywords (Music/Sound/Loud)
    if any(w in text_lower for w in ["loud", "noisy", "too loud", "רועש", "חזק", "הנמך", "תנמיך", "להנמיך", "מפריע", "volume"]):
        return "control_volume", {"action": "down"}
    if any(w in text_lower for w in ["volume up", "louder", "הגבר", "תגביר", "להגביה", "להגביר", "הגברת", "חזק יותר"]):
        return "control_volume", {"action": "up"}
    
    # Screenshot - MUST BE BEFORE brightness (both have "screen")
    if any(w in text_lower for w in ["screenshot", "take a screenshot", "צילום מסך", "תצלם מסך", "צלם מסך", "capture screen"]):
        return "take_screenshot", {}
    
    # Lock screen - MUST BE BEFORE brightness
    if any(w in text_lower for w in ["lock screen", "lock the screen", "lock my screen", "נעל את המסך", "תנעל את המסך", "תנעל לי את המסך"]):
        return "lock_screen", {}
    

    # Apps
    if any(w in text_lower for w in ["open chrome", "chrome", "כרום", "browser", "דפדפן"]):
        return "launch_app", {"app_name": "chrome"}
    if "spotify" in text_lower or "ספוטיפיי" in text_lower:
        if "play" in text_lower or "נגן" in text_lower:
            topic = text_lower
            for w in ["play", "on spotify", "spotify", "נגן", "בספוטיפיי", "ב", "user wants to", "i want to"]:
                topic = topic.replace(w, "")
            return "spotify_play", {"track_name": topic.strip() or "music"}
        return "launch_app", {"app_name": "spotify"}
    if "notepad" in text_lower or "פנקס" in text_lower:
        return "launch_app", {"app_name": "notepad"}
    if "calculator" in text_lower or "מחשבון" in text_lower:
        return "launch_app", {"app_name": "calc"}
    
    # YouTube
    if "youtube" in text_lower or "יוטיוב" in text_lower:
        topic = text_lower
        for w in ["play", "on youtube", "youtube", "נגן", "ביוטיוב", "user wants to", "i want to"]:
            topic = topic.replace(w, "")
        return "youtube_play", {"topic": topic.strip() or "music"}
    
    # Media control - SPECIFIC ORDER MATTERS
    if any(w in text_lower for w in ["next song", "next track", "שיר הבא", "הבא"]):
        return "control_media", {"action": "next"}
    if any(w in text_lower for w in ["previous song", "prev", "שיר קודם", "קודם"]):
        return "control_media", {"action": "previous"}
    # STOP - only for stop/pause, NOT mute (mute handled above)
    if any(w in text_lower for w in ["stop music", "stop the music", "pause", "עצור", "תעצור את המוזיקה", "השהה"]):
        return "stop_media", {}
    
    # Files - IMPORTANT: list before search
    if any(w in text_lower for w in ["what's in", "מה יש ב", "list files", "רשימת קבצים", "תיקיית ההורדות", "downloads folder"]):
        return "list_files", {"directory": "downloads"}
    if any(w in text_lower for w in ["file names", "שמות הקבצים", "files in"]):
        return "list_files", {"directory": "downloads"}
    # File search - multiple Hebrew triggers
    if any(w in text_lower for w in ["search file", "find file", "חפש קובץ", "מצא קובץ", "חפש לי קובץ"]):
        import re
        match = re.search(r'(?:called|named|בשם)\s+(\w+)', text_lower)
        if match:
            return "search_file", {"filename": match.group(1)}
        # Extract last word as filename
        return "search_file", {"filename": text_lower.split()[-1]}
    
    # Power/System - catch "turn off" and "turn the computer off" - SAFETY WRAPPER
    # CRITICAL: Check specific "turn off" targets FIRST to avoid accidental shutdown trigger
    
    # WiFi/Bluetooth Off shortcuts - Use KEYWORD COMBINATION matching to handle "the" etc.
    # Check if any "off" indicator + target word are both present
    off_indicators = ["off", "disable", "disconnect", "unplug", "cut off", "turn off", "תכבה", "תנתק", "כבה"]
    has_off_intent = any(w in text_lower for w in off_indicators)
    
    if has_off_intent:
        # Check WiFi first
        if any(w in text_lower for w in ["wifi", "wi-fi", "וויפי", "ווייפיי", "אינטרנט"]):
            # Make sure it's not about computer/shutdown
            if not any(w in text_lower for w in ["computer", "pc", "מחשב"]):
                return "toggle_wifi", {"state": "off"}
        
        # Check Bluetooth
        if any(w in text_lower for w in ["bluetooth", "בלוטוס", "בלוטות"]):
            return "toggle_bluetooth", {"state": "off"}

    # Disconnect Device catch-all - 'unplug' is translation of 'תנתק'
    if any(w in text_lower for w in ["disconnect", "unpair", "unplug", "תנתק", "נתק"]):
        if any(w in text_lower for w in ["headphone", "earphone", "buds", "אוזניות", "אוזניה"]):
            return "toggle_bluetooth", {"state": "off"} # Best effort
        if "wifi" in text_lower or "internet" in text_lower:
            return "toggle_wifi", {"state": "off"}
        if "bluetooth" in text_lower:
            return "toggle_bluetooth", {"state": "off"}
        # Default: assume bluetooth if just 'disconnect' with no target
        return "toggle_bluetooth", {"state": "off"}
        
    # Shutdown - Only triggers if NO wifi/bluetooth keyword is present
    is_shutdown = False
    if "shutdown" in text_lower or "shut down" in text_lower:
        is_shutdown = True
    elif "turn off" in text_lower:
        # Verify it's not "turn off wifi/music/light" etc.
        if any(w in text_lower for w in ["computer", "pc", "system", "machine", "מחשב"]):
            is_shutdown = True
        elif "turn off" == text_lower.strip(): # Just "turn off" alone
            is_shutdown = True
    # NEW: Catch "turn the computer off" / "turn my pc off" pattern (word in between)
    elif "turn" in text_lower and " off" in text_lower:
        if any(w in text_lower for w in ["computer", "pc", "system", "machine", "מחשב"]):
            is_shutdown = True
    elif "כבה את המחשב" in text_lower or "תכבה את המחשב" in text_lower:
        is_shutdown = True
        
    if is_shutdown:
        PENDING_ACTION = "shutdown_pc"
        PENDING_ARGS = {}
        return "ask_confirmation", {"question": "⚠️ WARNING: You asked to Shutdown. Are you sure? (Say 'Yes' to confirm)"}

    if any(w in text_lower for w in ["restart", "reboot", "הפעל מחדש"]):
        PENDING_ACTION = "restart_pc"
        PENDING_ARGS = {}
        return "ask_confirmation", {"question": "⚠️ WARNING: You asked to Restart. Are you sure? (Say 'Yes' to confirm)"}
    
    if any(w in text_lower for w in ["sleep mode", "put to sleep", "שינה"]):
        return "sleep_pc", {}
    # NOTE: lock_screen moved earlier (before brightness) - removed duplicate here
    
    # System status
    if any(w in text_lower for w in ["how is my pc", "system status", "איך המחשב", "סטטוס", "how is my computer"]):
        return "system_status", {}
    # Battery - dedicated shortcut  
    if any(w in text_lower for w in ["battery", "סוללה", "how much battery", "כמה סוללה"]):
        return "get_battery", {}
    
    # Network / Connectivity Shortcuts
    if any(w in text_lower for w in ["speed test", "speedtest", "bduka mehirut", "internet speed", "מהירות אינטרנט", "בדיקת מהירות", "internet is slow", "wifi is slow", "check internet", "check wifi", "אינטרנט איטי", "תבדוק את האינטרנט", "תבדוק את הוויפי", "תבדוק וויפי"]):
        return "check_internet_speed", {}
        
    if any(w in text_lower for w in ["wifi on", "enable wifi", "connect wifi", "תדליק וויפי", "תפעיל wifi", "תדליק את הוויפי", "תחבר וויפי", "תחבר את האינטרנט"]):
        return "toggle_wifi", {"state": "on"}
        
    # wifi off caught above for safety
         
    if any(w in text_lower for w in ["bluetooth on", "enable bluetooth", "connect bluetooth", "תדליק בלוטוס", "תפעיל בלוטוס", "תחבר בלוטוס", "תחבר את הבלוטוס"]):
        return "toggle_bluetooth", {"state": "on"}
        
    # bluetooth off caught above for safety
        
    # Connect Device (Headphones)
    if "connect" in text_lower or "pair" in text_lower or "תתחבר" in text_lower:
        if any(w in text_lower for w in ["headphone", "earphone", "buds", "אוזניות", "אוזניה"]):
            return "connect_device", {"device_type": "headphones"}
        if any(w in text_lower for w in ["speaker", "רמקול"]):
            return "connect_device", {"device_type": "speaker"}
        if any(w in text_lower for w in ["phone", "טלפון"]):
            return "connect_device", {"device_type": "phone"}

    # Basic Network Info - IMPORTANT: 'wifi' alone was too broad, removed it
    if any(w in text_lower for w in ["my ip", "ip address", "כתובת ip", "ה-ip שלי", "הכתובת ip"]):
        return "get_ip_address", {}
    if any(w in text_lower for w in ["wifi networks", "available networks", "what wifi", "list wifi", "רשתות wifi", "רשתות זמינות", "איזה רשתות"]):
        return "get_wifi_networks", {}
    
    # Vision - read screen
    if any(w in text_lower for w in ["read screen", "תקרא מה כתוב", "מה על המסך", "scan screen"]):
        return "read_screen", {}
    
    # Memory - ORDER MATTERS: recall before remember
    if any(w in text_lower for w in ["what do you remember", "what do you know", "מה אתה זוכר", "מה אתה יודע"]):
        return "recall_memories", {}
    if any(w in text_lower for w in ["forget", "תשכח", "שכח"]):
        fact = text_lower
        for w in ["forget", "the", "תשכח", "את", "ה"]:
            fact = fact.replace(w, "")
        return "forget_fact", {"fact_to_forget": fact.strip()}
    if any(w in text_lower for w in ["remember", "זכור", "תזכור"]):
        fact = text_lower
        for w in ["remember", "that", "זכור", "תזכור", "ש"]:
            fact = fact.replace(w, "")
        return "remember_fact", {"fact": fact.strip()}
    
    # News
    if any(w in text_lower for w in ["news", "חדשות", "telegram"]):
        return "telegram_news", {"channel": "all", "limit": 3}
    
    # Research/Search (last - catch-all)
    if any(w in text_lower for w in ["search for", "look for", "find information", "חפש מידע", "תחפש מידע"]):
        query = text_lower
        for w in ["search for", "look for", "find information", "about", "on", "חפש מידע", "על", "תחפש מידע"]:
            query = query.replace(w, "")
        return "smart_research", {"query": query.strip()}
    
    return None, None


# ============================================
# UNIFIED PROMPT
# ============================================
def build_unified_prompt(user_input: str, context: str, history: str = "") -> str:
    """Build the single unified analysis prompt."""
    
    # Note: We intentionally DON'T include history to avoid context bleeding
    return f"""Jarvis. {context}

User: "{user_input}"

Output JSON:
{{"cat":"X","type":"Y","conf":N,"tool":"...","args":"..."}}

cat: A=action, C=chat, M=remember/recall, K=question, U=unclear
type: Q=question, S=statement, C=command
conf: 1-100 (how confident)
tool: {build_tools_list()}, or N

Rules:
- "stop/pause/mute/shut" = stop_media (NEVER youtube_play)
- "I love X / I like X" = M (remember_fact) NOT K
- If input is short (< 5 words) and NOT a clear question (Who/What/Where...), cat=C (Chat).
- Negations ("I didn't", "No", "Not") = C (Chat).
- "K" (Knowledge) is ONLY for clear research questions about facts/events.
- If conf < 60, set cat=U

Examples:
- "stop" -> {{"cat":"A","type":"C","conf":95,"tool":"stop_media","args":""}}
- "I love pizza" -> {{"cat":"M","type":"S","conf":90,"tool":"remember_fact","args":"loves pizza"}}
- "what?" -> {{"cat":"U","type":"Q","conf":30,"tool":"N","args":""}}
- "I didn't ask" -> {{"cat":"C","type":"S","conf":90,"tool":"N","args":""}}
- "Who is the president?" -> {{"cat":"K","type":"Q","conf":95,"tool":"smart_research","args":"current president"}}

JSON:"""


def parse_unified_response(response: str) -> dict:
    """Parse the unified JSON response."""
    try:
        # Find JSON in response
        match = re.search(r'\{[^{}]+\}', response)
        if match:
            parsed = json.loads(match.group())
            # Normalize conf to int
            if "conf" in parsed:
                try:
                    parsed["conf"] = int(parsed["conf"])
                except:
                    parsed["conf"] = 50
            return parsed
    except:
        pass
    
    # Fallback - unclear
    return {
        "cat": "U",
        "type": "Q",
        "conf": 30,
        "tool": "N",
        "args": ""
    }


# ============================================
# RESPONSE PROMPT
# ============================================
def build_response_prompt(intent: str, result: str, context: str) -> str:
    """Build the response generation prompt."""
    
    # DETECT CONTENT TOOLS - These need full output, not summaries
    content_tools = ["telegram_news", "list_files", "read_file", "search_file", "smart_research", "read_screen", "recall_memories", "system_status", "get_battery"]
    is_content_request = any(t in intent for t in content_tools)
    
    if is_content_request:
        return f"""You are Jarvis. The user asked for information/content.
        
Context: {context}
Tool Result:
{result}

TASK: Present the result to the user clearly.
- If it's news/files/text: Show the content in a readable list or summary.
- Do NOT be concise. Show the information requested.
- Address user as "Sir"."""
    
    # Default prompt for Actions - HUMANIZED / BUTLER PERSOANLITY
    return f"""You are Jarvis, a loyal and witty British butler. The user made a request and here is the result:

Intent: {intent}
Result: {result}

TASK: Reply to the user (Sir) about the result.
PERSONALITY RULES:
1. Be natural, polite, and slightly witty.
2. NEVER be robotic. Avoid "Done" or "Task completed" as the whole sentence.
3. VARY your phrasing! Never say the same thing twice.
4. If the result is a Time (e.g., 14:30), convert it to spoken words (e.g., "It is half past two, Sir").
5. Keep it brief (1-2 sentences), but classy.

Examples of good responses:
- "As you wish, Sir. The volume has been lowered."
- "The Wi-Fi is now off, Sir. I hope you enjoy the silence."
- "It is a quarter to three, Sir."
- "I have removed that file from your sight."
"""


# ============================================
# MAIN PROCESSING FUNCTION
# ============================================

def generate_fallback_response(llm_invoke: Callable, user_input: str) -> str:
    """Generate a polite, varied fallback response when processing fails."""
    prompt = f"""You are Jarvis, a British butler. 
    Task: Apologize that you could not process the user's request: "{user_input}"
    Rules:
    1. Be polite and varied.
    2. Examples: "I do apologize, Sir, but I'm having trouble processing that.", "My apologies, Sir, I seem to have hit a snag."
    3. One short sentence only.
    """
    return llm_invoke(prompt).strip().strip('"')

def layered_process(
    user_input: str,
    llm_invoke: Callable[[str], str],
    tool_executor: Callable[[str, Dict], str],
    conversation_history: List[Dict] = None,
    original_hebrew: bool = False,
    last_action: str = None
) -> str:
    """
    Unified layer processing.
    Returns final response string.
    """
    start_time = time.time()
    
    print(f"\n{'='*60}")
    print(f"  JARVIS UNIFIED SYSTEM v3")
    print(f"  Input: {user_input}")
    print(f"{'='*60}")
    
    # === CONTEXT ===
    now = datetime.now()
    day_name = now.strftime("%A")
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%H:%M")
    
    context = f"Today: {day_name}, {date_str}, {time_str}. Israel."
    print(f"[CTX] {context}")
    
    # === NEW: ZERO-LATENCY SEMANTIC ROUTER ===
    try:
        from semantic_router import decide_route
        route_result = decide_route(user_input)
        
        if route_result and route_result.get("route") == "action":
            r_tool = route_result.get("tool")
            r_args = route_result.get("args", {})
            print(f"[FAST-ROUTER] Executing → {r_tool}({r_args})")
            
            # Execute tool
            try:
                result = tool_executor(r_tool, r_args)
                print(f"[EXEC] ✓ {str(result)[:50]}...")
            except Exception as e:
                result = f"Error: {e}"
                print(f"[EXEC] ✗ {result}")
            
            # Generate response
            resp_prompt = build_response_prompt(r_tool, result, context)
            response = llm_invoke(resp_prompt).strip().strip('"')
            
            # Save to session
            _save_turn(user_input, r_tool, response, r_tool)
            
            elapsed = time.time() - start_time
            print(f"[TIME] Semantic Router Finished in {elapsed:.2f}s")
            return response
            
    except ImportError as e:
        print(f"[ROUTER] Semantic router module missing: {e}")
    except Exception as e:
        print(f"[ROUTER] Semantic router error: {e}")
        
    # === STEP 1: SHORTCUTS (No LLM - Fallback) ===
    # Pass context to shortcuts
    tool_name, tool_args = check_shortcuts(user_input, last_action=last_action)
    
    if tool_name:
        print(f"[SHORTCUT] → {tool_name}({tool_args})")
        
        # Execute tool
        try:
            result = tool_executor(tool_name, tool_args)
            print(f"[EXEC] ✓ {result[:50]}...")
        except Exception as e:
            result = f"Error: {e}"
            print(f"[EXEC] ✗ {result}")
        
        # Generate response
        resp_prompt = build_response_prompt(tool_name, result, context)
        response = llm_invoke(resp_prompt).strip().strip('"')
        
        # Save to session
        _save_turn(user_input, tool_name, response, tool_name)
        
        print(f"[TIME] {time.time() - start_time:.2f}s")
        return response
    
    # === STEP 2: INTENT LAYER - Understand what user wants ===
    # SKIP for greetings and very short messages (likely chat, not commands)
    input_lower = user_input.lower().strip()
    greeting_words = ["hi", "hey", "hello", "yo", "sup", "good morning", "good afternoon", "good evening",
                      "הי", "היי", "שלום", "אהלן", "בוקר טוב", "ערב טוב", "מה נשמע", "מה קורה"]
    is_greeting = any(input_lower == g or input_lower.startswith(g + " ") or input_lower.startswith(g + ",") for g in greeting_words)
    is_too_short = len(input_lower.split()) <= 2 and not any(c.isdigit() for c in input_lower)
    
    if is_greeting or (is_too_short and "?" not in user_input):
        print(f"[INTENT] Skipped (greeting/short message)")
        # Fall through to unified analysis for chat
    else:
        # Actually extract intent for commands
        intent_prompt = f"""User said: "{user_input}"
What does the user want to DO? Reply in ONE short English sentence starting with "User wants to".
If this is just a greeting, casual chat, or emotional statement (not a command), reply "CHAT".
Examples:
- "User wants to set screen brightness to 70%"
- "User wants to turn off Bluetooth"
- "CHAT" (for "Hi", "How are you", "I am sad", "I feel tired")
Reply ONLY the sentence, nothing else."""
    
        print(f"[INTENT] Extracting...")
        intent = llm_invoke(intent_prompt).strip().strip('"')
        print(f"[INTENT] {intent}")
        
        # Skip if LLM detected chat
        if intent.upper() != "CHAT" and "wants to" in intent.lower():
            # === STEP 2.5: Match intent to shortcuts ===
            intent_tool, intent_args = check_shortcuts(intent, last_action=last_action)
            
            if intent_tool:
                print(f"[INTENT→SHORTCUT] → {intent_tool}({intent_args})")
                try:
                    result = tool_executor(intent_tool, intent_args)
                    print(f"[EXEC] ✓ {result[:50]}...")
                except Exception as e:
                    result = f"Error: {e}"
                    print(f"[EXEC] ✗ {result}")
                
                resp_prompt = build_response_prompt(intent_tool, result, context)
                response = llm_invoke(resp_prompt).strip().strip('"')
                _save_turn(user_input, intent_tool, response, intent_tool)
                print(f"[TIME] {time.time() - start_time:.2f}s")
                return response
    
    # === UNIFIED LLM ANALYSIS ===
    print("[UNIFIED] Analyzing...")
    
    # Note: No history passed - prevents context bleeding
    prompt = build_unified_prompt(user_input, context, "")
    print(f"[PROMPT] {len(prompt)} chars")
    
    raw_response = llm_invoke(prompt)
    analysis = parse_unified_response(raw_response)
    
    cat = analysis.get("cat", "C")
    msg_type = analysis.get("type", "Q")
    conf = analysis.get("conf", 50)
    tool = analysis.get("tool", "N")
    args_str = analysis.get("args", "")
    
    print(f"[ANALYSIS] cat={cat} type={msg_type} conf={conf} tool={tool} args={args_str}")
    
    # === CONFIDENCE CHECK ===
    if conf < 50 or cat == "U":
        # Low confidence - ask for clarification DYNAMICALLY
        print(f"[UNCLEAR] Confidence too low ({conf}), asking clarification")
        
        clarify_prompt = f"""You are Jarvis, a British butler. The user said: "{user_input}"
        I am not sure what they want.
        TASK: Politely ask for clarification.
        RULES:
        1. Be polite and apologetic but not weak.
        2. VARY your phrasing (e.g., "I beg your pardon?", "Could you rephrase that, Sir?", "I'm afraid I didn't quite catch that.")
        3. Do NOT repeat the same phrase.
        4. One short sentence."""
        
        response = llm_invoke(clarify_prompt).strip().strip('"')
        _save_turn(user_input, "unclear", response, None)
        return response
    
    # === ROUTE: If tool found, ALWAYS execute (regardless of category) ===
    result = None
    used_tool = None
    
    if tool and tool != "N" and tool.lower() not in ["n", "none", "no"]:
        # Parse args
        if args_str and args_str.lower() not in ["none", "empty", ""]:
            # Try to make dict
            if "=" in args_str:
                parts = args_str.split("=")
                tool_args = {parts[0].strip(): parts[1].strip()}
            else:
                # Guess arg name
                if tool == "launch_app":
                    tool_args = {"app_name": args_str}
                elif tool == "set_volume":
                    tool_args = {"action": args_str}
                elif tool in ["youtube_play", "spotify_play"]:
                    tool_args = {"topic": args_str} if tool == "youtube_play" else {"track_name": args_str}
                elif tool in ["remember_fact", "forget_fact"]:
                    tool_args = {"fact": args_str}
                elif tool == "smart_research":
                    tool_args = {"query": args_str}
                else:
                    tool_args = {}
        else:
            tool_args = {}
        
        # Execute
        try:
            result = tool_executor(tool, tool_args)
            used_tool = tool
            print(f"[EXEC] ✓ {tool}: {str(result)[:50]}...")
        except Exception as e:
            result = f"Error: {e}"
            print(f"[EXEC] ✗ {tool}: {e}")
    
    elif cat == "M":  # Memory
        # S=Statement (save), Q=Question (recall)
        if msg_type == "S" or "remember" in user_input.lower() or "זכור" in user_input.lower():
            # Save as fact - extract meaningful part
            fact = args_str if args_str else user_input
            result = tool_executor("remember_fact", {"fact": fact})
            used_tool = "remember_fact"
        elif "forget" in user_input.lower() or "שכח" in user_input.lower():
            result = tool_executor("forget_fact", {"fact_to_forget": user_input})
            used_tool = "forget_fact"
        else:
            result = tool_executor("recall_memories", {})
            used_tool = "recall_memories"
        print(f"[MEMORY] {used_tool}: {str(result)[:50]}...")
    
    elif cat == "K":  # Knowledge
        # Use research
        result = tool_executor("smart_research", {"query": user_input})
        used_tool = "smart_research"
        print(f"[KNOWLEDGE] Research: {str(result)[:50]}...")
    
    else:  # Chat
        result = None
        print(f"[CHAT] Direct response")
    
    # === GENERATE RESPONSE ===
    intent_desc = used_tool or cat  # Use tool name or category as intent
    if result:
        resp_prompt = build_response_prompt(intent_desc, str(result)[:200], context)
    else:
        resp_prompt = f"""{context}
User said: "{user_input}"

Reply as Jarvis (British butler, brief, polite). Address as "Sir". 1-2 sentences."""
    
    response = llm_invoke(resp_prompt).strip().strip('"')
    
    # Clean response
    if response.startswith("Jarvis:"):
        response = response[7:].strip()
    
    # Save to session
    _save_turn(user_input, intent_desc, response, used_tool)
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  COMPLETE in {elapsed:.2f}s")
    print(f"  Category: {cat} | Tool: {used_tool or 'None'}")
    print(f"{'='*60}\n")
    
    return response


def _save_turn(user_input: str, intent: str, response: str, tool_used: str):
    """Save turn to session memory."""
    try:
        from session_memory import add_turn
        add_turn(
            user_input=user_input,
            intent=intent,
            response=response[:150] if response else "",
            tool_used=tool_used
        )
    except Exception as e:
        print(f"[SESSION] Save failed: {e}")


# ============================================
# TEST
# ============================================
if __name__ == "__main__":
    def mock_llm(prompt):
        print(f"[MOCK LLM] {prompt[:100]}...")
        return '{"cat": "C", "intent": "greeting", "tool": "N", "args": ""}'
    
    def mock_executor(tool_name, args):
        return f"Executed {tool_name}"
    
    result = layered_process(
        "what time is it",
        mock_llm,
        mock_executor
    )
    print(f"RESULT: {result}")
