"""
Jarvis Sound System - Smart audio feedback with looping sounds
Sounds only play if action takes > 1 second
Thinking/searching sounds loop until task completes
"""
import os
import threading
import time

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(PROJECT_DIR, "sounds")

# Map sound names to files (based on user's files)
SOUND_FILES = {
    "startup": "start.mp3",
    "shutdown": "system down.mp3",
    "thinking": "thinking.mp3",
    "search": "searching internet.mp3",
    "computer": "woring on computer.mp3",
    "success": "success.mp3",
}

# Global state
SOUNDS_ENABLED = True
_current_loop_thread = None
_stop_loop = threading.Event()

def get_sound_path(sound_name: str) -> str:
    """Get the full path to a sound file."""
    filename = SOUND_FILES.get(sound_name)
    if not filename:
        return None
    return os.path.join(SOUNDS_DIR, filename)

def play_sound_once(sound_name: str):
    """Play a sound once (non-blocking, no window)."""
    if not SOUNDS_ENABLED:
        return
    
    path = get_sound_path(sound_name)
    if not path or not os.path.exists(path):
        print(f"   ⚠️ Sound not found: {sound_name}")
        return
    
    try:
        from playsound import playsound
        # playsound blocks by default, run in thread for non-blocking
        playsound(path, block=False)
        print(f"   🔊 Playing: {sound_name}")
    except ImportError:
        print("   ⚠️ playsound not installed. Run: pip install playsound==1.2.2")
    except Exception as e:
        print(f"   ⚠️ Sound error: {e}")

def play_sound_async(sound_name: str):
    """Play a sound in background thread."""
    thread = threading.Thread(target=play_sound_once, args=(sound_name,), daemon=True)
    thread.start()

def _loop_sound(sound_name: str, delay_before_start: float = 1.0):
    """Internal: Loop a sound until stopped. Only starts after delay."""
    global _stop_loop
    
    # Wait before starting (only play if action is slow)
    start_wait = time.time()
    while time.time() - start_wait < delay_before_start:
        if _stop_loop.is_set():
            return
        time.sleep(0.1)
    
    # If we got here, action is taking long - start looping
    path = get_sound_path(sound_name)
    if not path or not os.path.exists(path):
        return
    
    try:
        import pygame
        pygame.mixer.init()
        sound = pygame.mixer.Sound(path)
        
        while not _stop_loop.is_set():
            sound.play()
            # Wait for sound to finish (approximate)
            time.sleep(2.0)  # Most sounds are ~2 seconds
            
        pygame.mixer.quit()
    except ImportError:
        # Fallback: just play once
        play_sound_once(sound_name)
    except:
        pass

def start_loop_sound(sound_name: str, delay: float = 1.0):
    """
    Start looping a sound (thinking, searching, etc.)
    Only starts playing after 'delay' seconds - if task finishes faster, no sound.
    """
    global _current_loop_thread, _stop_loop
    
    if not SOUNDS_ENABLED:
        return
    
    stop_loop_sound()  # Stop any existing loop
    
    _stop_loop = threading.Event()
    _current_loop_thread = threading.Thread(
        target=_loop_sound,
        args=(sound_name, delay),
        daemon=True
    )
    _current_loop_thread.start()

def stop_loop_sound():
    """Stop any currently looping sound."""
    global _current_loop_thread, _stop_loop
    
    _stop_loop.set()
    if _current_loop_thread:
        _current_loop_thread.join(timeout=0.5)
        _current_loop_thread = None

# === CONVENIENCE FUNCTIONS ===

def sound_startup():
    """Play startup sound."""
    play_sound_async("startup")

def sound_shutdown():
    """Play shutdown sound."""
    play_sound_once("shutdown")

def sound_success():
    """Play success sound."""
    play_sound_async("success")

def start_thinking():
    """Start thinking loop (after 200ms delay)."""
    start_loop_sound("thinking", delay=0.2)

def start_searching():
    """Start internet search loop (after 200ms delay)."""
    start_loop_sound("search", delay=0.2)

def start_computer_action():
    """Start computer action loop (after 200ms delay)."""
    start_loop_sound("computer", delay=0.2)

def stop_action_sound():
    """Stop any action sound and play success."""
    stop_loop_sound()
    sound_success()

def enable_sounds():
    global SOUNDS_ENABLED
    SOUNDS_ENABLED = True
    print("🔊 Sounds enabled")

def disable_sounds():
    global SOUNDS_ENABLED
    SOUNDS_ENABLED = False
    stop_loop_sound()
    print("🔇 Sounds disabled")
