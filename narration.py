"""
Jarvis Narration System - Announce actions as they happen
"""
from sounds import play_sound

# Narration messages for different action types
NARRATION = {
    "search_start": "מחפש...",
    "search_done": "מצאתי.",
    "file_search": "מחפש קבצים...",
    "file_found": "נמצא.",
    "opening": "פותח...",
    "opened": "נפתח.",
    "changing": "משנה...",
    "changed": "בוצע.",
    "moving": "מעביר...",
    "moved": "הועבר.",
    "deleting": "מוחק...",
    "deleted": "נמחק.",
    "setting": "מגדיר...",
    "set": "הוגדר.",
    "thinking": "רגע...",
    "done": "בוצע.",
    "error": "שגיאה.",
}

def narrate(action: str, speak_func=None):
    """
    Narrate an action - both print and optionally speak.
    
    Args:
        action: Key from NARRATION dict or custom message
        speak_func: Optional TTS function to speak the narration
    """
    message = NARRATION.get(action, action)
    
    # Print to console
    print(f"   📢 {message}")
    
    # Play appropriate sound
    if "search" in action:
        play_sound("search")
    elif action in ["done", "opened", "set", "changed"]:
        play_sound("success")
    elif action == "error":
        play_sound("error")
    else:
        play_sound("action")
    
    # Speak if function provided
    if speak_func:
        speak_func(message)

def narrate_step(step_number: int, total_steps: int, description: str, speak_func=None):
    """
    Narrate a step in a multi-step process.
    
    Args:
        step_number: Current step (1-indexed)
        total_steps: Total number of steps
        description: What this step does
        speak_func: Optional TTS function
    """
    message = f"שלב {step_number} מתוך {total_steps}: {description}"
    print(f"   📢 {message}")
    
    play_sound("action")
    
    if speak_func:
        speak_func(description)

class ActionNarrator:
    """Context manager for narrating multi-step actions."""
    
    def __init__(self, action_name: str, speak_func=None):
        self.action_name = action_name
        self.speak_func = speak_func
        self.steps = []
        self.current_step = 0
    
    def add_step(self, description: str):
        """Add a step to the action."""
        self.steps.append(description)
    
    def start(self):
        """Start the action."""
        if self.speak_func:
            self.speak_func(f"מתחיל {self.action_name}")
        print(f"   🚀 Starting: {self.action_name}")
        play_sound("action")
    
    def next_step(self, description: str = None):
        """Move to next step and narrate it."""
        self.current_step += 1
        
        if description:
            step_desc = description
        elif self.current_step <= len(self.steps):
            step_desc = self.steps[self.current_step - 1]
        else:
            step_desc = f"Step {self.current_step}"
        
        message = step_desc
        print(f"   📢 [{self.current_step}] {message}")
        
        if self.speak_func:
            self.speak_func(step_desc)
    
    def complete(self, message: str = "בוצע"):
        """Complete the action."""
        print(f"   ✅ {message}")
        play_sound("success")
        
        if self.speak_func:
            self.speak_func(message)
    
    def fail(self, error: str = "שגיאה"):
        """Action failed."""
        print(f"   ❌ {error}")
        play_sound("error")
        
        if self.speak_func:
            self.speak_func(error)
