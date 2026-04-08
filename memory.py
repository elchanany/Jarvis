"""
Jarvis Memory System - Persistent user preferences and conversation memory
"""
import os
import json
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(PROJECT_DIR, "user_profile.json")

# Default profile
DEFAULT_PROFILE = {
    "user_name": "User",
    "preferences": {
        "music_genre": "any",
        "browser": "chrome",
        "editor": "vscode",
    },
    "facts": [],  # Things the user told Jarvis to remember
    "last_session": None,
}

def load_memory() -> dict:
    """Load user profile from file."""
    if not os.path.exists(MEMORY_FILE):
        save_memory(DEFAULT_PROFILE)
        return DEFAULT_PROFILE.copy()
    
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return DEFAULT_PROFILE.copy()

def save_memory(profile: dict):
    """Save user profile to file."""
    profile["last_session"] = datetime.now().isoformat()
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

def get_user_name() -> str:
    """Get user's name."""
    profile = load_memory()
    return profile.get("user_name", "User")

def set_user_name(name: str) -> str:
    """Set user's name."""
    profile = load_memory()
    profile["user_name"] = name
    save_memory(profile)
    return f"I'll remember your name is {name}"

def get_preference(key: str) -> str:
    """Get a user preference."""
    profile = load_memory()
    prefs = profile.get("preferences", {})
    return prefs.get(key, "not set")

def set_preference(key: str, value: str) -> str:
    """Set a user preference."""
    profile = load_memory()
    if "preferences" not in profile:
        profile["preferences"] = {}
    profile["preferences"][key] = value
    save_memory(profile)
    return f"Preference saved: {key} = {value}"

def remember_fact(fact: str) -> str:
    """Remember a fact about the user."""
    profile = load_memory()
    if "facts" not in profile:
        profile["facts"] = []
    profile["facts"].append({
        "fact": fact,
        "date": datetime.now().isoformat()
    })
    save_memory(profile)
    return f"I'll remember: {fact}"

def get_facts() -> list:
    """Get all remembered facts."""
    profile = load_memory()
    return profile.get("facts", [])

def forget_fact(keyword: str) -> str:
    """Forget a fact containing keyword."""
    profile = load_memory()
    facts = profile.get("facts", [])
    original_count = len(facts)
    facts = [f for f in facts if keyword.lower() not in f["fact"].lower()]
    profile["facts"] = facts
    save_memory(profile)
    removed = original_count - len(facts)
    return f"Forgot {removed} fact(s) containing '{keyword}'"

def get_memory_context() -> str:
    """Get memory context to inject into LLM prompt."""
    profile = load_memory()
    
    context = f"User's name: {profile.get('user_name', 'User')}\n"
    
    prefs = profile.get("preferences", {})
    if prefs:
        context += "Preferences:\n"
        for k, v in prefs.items():
            context += f"  - {k}: {v}\n"
    
    facts = profile.get("facts", [])
    if facts:
        context += "Things to remember:\n"
        for f in facts[-5:]:  # Last 5 facts
            context += f"  - {f['fact']}\n"
    
    return context

def clear_memory() -> str:
    """Clear all memory (reset to default)."""
    save_memory(DEFAULT_PROFILE)
    return "Memory cleared"

# Memory tools for the LLM
MEMORY_TOOLS = {
    "remember": {
        "function": remember_fact,
        "description": "Remember something the user tells you",
        "parameters": ["fact"]
    },
    "set_user_name": {
        "function": set_user_name,
        "description": "Set the user's name",
        "parameters": ["name"]
    },
    "set_preference": {
        "function": set_preference,
        "description": "Save a user preference",
        "parameters": ["key", "value"]
    },
}
