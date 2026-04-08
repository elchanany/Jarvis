# session_memory.py
# ==================
# Short-term session memory manager for JARVIS
# Tracks conversation summaries within a session

import os
import json
from datetime import datetime
from typing import List, Dict, Optional

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FILE = os.path.join(PROJECT_DIR, "session_memory.json")

# In-memory cache for current session
_session_cache: Dict = None


def _load_session() -> Dict:
    """Load session from file or create new."""
    global _session_cache
    
    if _session_cache is not None:
        return _session_cache
    
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                _session_cache = json.load(f)
                return _session_cache
        except:
            pass
    
    # New session
    _session_cache = {
        "session_start": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "turns": []
    }
    return _session_cache


def _save_session():
    """Save session to file."""
    global _session_cache
    if _session_cache:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(_session_cache, f, ensure_ascii=False, indent=2)


def add_turn(user_input: str, intent: str, response: str, tool_used: str = None):
    """
    Add a conversation turn to session memory.
    
    Args:
        user_input: What the user said
        intent: What we understood they wanted
        response: What JARVIS responded
        tool_used: Tool executed (if any)
    """
    session = _load_session()
    
    turn_num = len(session["turns"]) + 1
    
    turn = {
        "turn": turn_num,
        "time": datetime.now().strftime("%H:%M"),
        "user": user_input[:100],  # Truncate long inputs
        "intent": intent[:100],
        "response": response[:150],
        "tool": tool_used
    }
    
    session["turns"].append(turn)
    
    # Keep only last 10 turns to prevent bloat
    if len(session["turns"]) > 10:
        session["turns"] = session["turns"][-10:]
    
    _save_session()
    print(f"[SESSION] Saved turn #{turn_num}")


def get_session_summary() -> str:
    """
    Get a formatted summary of recent conversation for context injection.
    
    Returns:
        Formatted string of recent turns
    """
    session = _load_session()
    
    if not session["turns"]:
        return ""
    
    lines = ["=== SESSION MEMORY (Recent Turns) ==="]
    
    for turn in session["turns"][-5:]:  # Last 5 turns
        lines.append(f"[{turn['time']}] User: {turn['user']}")
        lines.append(f"       Intent: {turn['intent']}")
        lines.append(f"       Response: {turn['response']}")
        if turn.get("tool"):
            lines.append(f"       Tool: {turn['tool']}")
    
    return "\n".join(lines)


def get_last_turn() -> Optional[Dict]:
    """Get the most recent turn."""
    session = _load_session()
    if session["turns"]:
        return session["turns"][-1]
    return None


def clear_session():
    """Clear session memory (for 'reset system' command)."""
    global _session_cache
    _session_cache = {
        "session_start": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "turns": []
    }
    _save_session()
    print("[SESSION] Memory cleared")


def get_turn_count() -> int:
    """Get number of turns in current session."""
    session = _load_session()
    return len(session["turns"])


# ============================================
# TEST
# ============================================
if __name__ == "__main__":
    clear_session()
    
    add_turn(
        user_input="Hi",
        intent="Greeting",
        response="Hello Sir, how may I assist you?"
    )
    
    add_turn(
        user_input="make music quieter",
        intent="Lower volume",
        response="Volume lowered, Sir.",
        tool_used="set_volume"
    )
    
    print("\n" + get_session_summary())
