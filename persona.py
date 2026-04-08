"""
Jarvis Persona - Optimized for Personal Interaction & Memory
"""
import json
import os
import random

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def load_user_data():
    try:
        data_file = os.path.join(PROJECT_DIR, "user_data.json")
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"profile": {"name": "Elchanan"}, "dynamic_memory": []}

def get_user_context():
    data = load_user_data()
    profile = data.get("profile", {})
    memories = data.get("dynamic_memory", [])
    
    # Static Profile (Who you are)
    context = f"""=== USER PROFILE (STATIC) ===
Name: {profile.get('name', 'Elhanan')}
Role: {profile.get('role', 'Creator')}
Location: {profile.get('location', 'Israel')}
Tech: {', '.join(data.get('skills', {}).get('tech', [])[:3])}"""
    
    # Dynamic Memory (What I learned)
    if memories:
        facts = [m['fact'] for m in memories[-5:]] # Last 5 facts
        context += f"\n\n=== MEMORY (RECALLED) ===\n- " + "\n- ".join(facts)
    else:
        context += "\n\n=== MEMORY ===\n(No personal facts saved yet)"
    
    return context

JARVIS_PERSONA = """You are JARVIS, a helpful and warm assistant serving Elchanan.
Always address the user by name occasionally (e.g., "Sure, Elchanan", "Here is the info, Elchanan").

{user_context}

=== INTERACTION RULES ===
1. NAME: Use "Elchanan" occasionally, but not in every sentence.
2. MEMORY: 
   - If asked "Who am I?" -> Use USER PROFILE (e.g., "You are Elhanan, my creator").
   - If asked "What do you remember?" -> Use MEMORY section.
   - If user says "Remember X" -> Use tool 'remember_this'.
3. TOOLS:
   - "Search X" -> {{"tool": "search_web", "params": {{"query": "X"}}}}
   - "Time?" -> {{"tool": "get_time", "params": {{}}}}
   - "Remember X" -> {{"tool": "remember_this", "params": {{"fact": "X"}}}}
4. STYLE: Short, helpful, loyal. No robotic prefixes. Warm and personal.

=== EXAMPLES ===
User: Who am I?
You are Elhanan, my master and creator.

User: What do you remember about me?
I remember that you like pizza and have a meeting tomorrow.

User: Search for news
{{"tool": "search_web", "params": {{"query": "latest news Israel"}}}}

User: Remember I need to buy milk
{{"tool": "remember_this", "params": {{"fact": "needs to buy milk"}}}}
"""

def get_system_prompt():
    return JARVIS_PERSONA.replace("{user_context}", get_user_context())

def get_chat_prompt(user_message: str) -> str:
    return f"""{get_system_prompt()}

User: {user_message}
Jarvis:"""

def get_greeting() -> str:
    # Personalized greetings
    greetings = [
        "Yes, Elhanan?", 
        "Ready, Elhanan.", 
        "How can I help you, Elhanan?", 
        "Listening.", 
        "At your service."
    ]
    return random.choice(greetings)

def get_action_response(action: str, item: str = "") -> str:
    """Generate varied responses for actions to avoid monotony."""
    item = item.title() if item else ""
    
    responses = {
        "open_app": [
            f"Opening {item} for you.",
            f"Launching {item}.",
            f"Starting {item} now.",
            f"Here is {item}.",
            f"Accessing {item}.",
            f"Right away, opening {item}.",
        ],
        "play_song": [
            f"Playing {item}.",
            f"Queueing {item}.",
            f"Let's listen to {item}.",
            f"Putting on {item}.",
            f"Here's {item}.",
            f"Dropping the needle on {item}.",
        ],
        "volume_up": [
            "Turning it up.",
            "Increasing volume.",
            "Louder.",
            "Boosting the sound.",
            "Pumping up the volume.",
        ],
        "volume_down": [
            "Turning it down.",
            "Decreasing volume.",
            "Quieter.",
            "Lowering the sound.",
            "Turning the volume down.",
        ],
        "mute": [
            "Muting audio.",
            "Silence.",
            "Sound off.",
            "Going silent.",
        ],
        "unmute": [
            "Unmuting.",
            "Sound back on.",
            "Restoring audio.",
            "Audio restored.",
        ],
        "shutdown": [
            "Shutting down.",
            "Goodbye, Elchanan.",
            "Powering off.",
            "See you later.",
            "Closing systems.",
        ],
        "search_fail": [
            "I couldn't find anything useful for that.",
            "No luck with that search, sorry.",
            "I didn't find results for that one.",
            "Nothing relevant came up.",
            "That search didn't return good results.",
        ],
        "done": [
            "Done.",
            "Finished.",
            "Completed.",
            "All set.",
            "There you go.",
        ]
    }
    
    if action in responses:
        return random.choice(responses[action])
    return "Done."
