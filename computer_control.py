# computer_control.py
# ==================
# Jarvis Agentic Computer Control — Full "Robot Mode"
# Gives the AI eyes and hands to control the computer like a human.

import os
import io
import time
import json
import base64
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(PROJECT_DIR, "uploads", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

OLLAMA_BASE = "http://127.0.0.1:11434"


# ═══════════════════════════════════════════
#  LOW-LEVEL ACTIONS (pyautogui wrappers)
# ═══════════════════════════════════════════

def take_screenshot_raw():
    """Capture the screen and return (filepath, base64_string)."""
    try:
        import pyautogui
        from PIL import Image

        img = pyautogui.screenshot()
        # Resize to 1280x720 for faster model processing
        img = img.resize((1280, 720), Image.LANCZOS)

        filename = f"screen_{int(time.time()*1000)}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        img.save(filepath, "PNG")

        # Convert to base64 for vision model
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return filepath, b64
    except Exception as e:
        return None, f"Screenshot error: {e}"


def click_at(x, y, button="left", clicks=1):
    """Click at screen coordinates."""
    try:
        import pyautogui
        pyautogui.click(x, y, button=button, clicks=clicks)
        return f"Clicked ({button}) at ({x}, {y})"
    except Exception as e:
        return f"Click error: {e}"


def double_click_at(x, y):
    """Double-click at screen coordinates."""
    return click_at(x, y, clicks=2)


def right_click_at(x, y):
    """Right-click at screen coordinates."""
    return click_at(x, y, button="right")


def type_text(text, interval=0.02):
    """Type text with keyboard."""
    try:
        import pyautogui
        pyautogui.typewrite(text, interval=interval) if text.isascii() else pyautogui.write(text)
        return f"Typed: {text[:50]}..."
    except Exception as e:
        # Fallback for non-ASCII (Hebrew etc.)
        try:
            import pyperclip
            import pyautogui
            pyperclip.copy(text)
            pyautogui.hotkey('ctrl', 'v')
            return f"Pasted text: {text[:50]}..."
        except Exception as e2:
            return f"Type error: {e2}"


def press_key(key):
    """Press a single key."""
    try:
        import pyautogui
        pyautogui.press(key)
        return f"Pressed key: {key}"
    except Exception as e:
        return f"Key press error: {e}"


def hotkey(*keys):
    """Press a key combination like Ctrl+C."""
    try:
        import pyautogui
        pyautogui.hotkey(*keys)
        return f"Hotkey: {'+'.join(keys)}"
    except Exception as e:
        return f"Hotkey error: {e}"


def scroll_screen(direction="down", amount=3):
    """Scroll up or down."""
    try:
        import pyautogui
        clicks = -amount if direction == "down" else amount
        pyautogui.scroll(clicks * 100)
        return f"Scrolled {direction} by {amount}"
    except Exception as e:
        return f"Scroll error: {e}"


def move_mouse(x, y):
    """Move mouse cursor to position."""
    try:
        import pyautogui
        pyautogui.moveTo(x, y, duration=0.3)
        return f"Mouse moved to ({x}, {y})"
    except Exception as e:
        return f"Mouse move error: {e}"


def drag_to(x1, y1, x2, y2, duration=0.5):
    """Drag from (x1,y1) to (x2,y2)."""
    try:
        import pyautogui
        pyautogui.moveTo(x1, y1)
        pyautogui.drag(x2 - x1, y2 - y1, duration=duration)
        return f"Dragged from ({x1},{y1}) to ({x2},{y2})"
    except Exception as e:
        return f"Drag error: {e}"


def get_screen_size():
    """Get screen resolution."""
    try:
        import pyautogui
        w, h = pyautogui.size()
        return f"Screen size: {w}x{h}"
    except Exception as e:
        return f"Screen size error: {e}"


def get_mouse_position():
    """Get current mouse position."""
    try:
        import pyautogui
        x, y = pyautogui.position()
        return f"Mouse at ({x}, {y})"
    except Exception as e:
        return f"Position error: {e}"


# ═══════════════════════════════════════════
#  VISION — Ask the model to analyze a screenshot
# ═══════════════════════════════════════════

def analyze_screen(question="What do you see on the screen?", model="gemma4:e4b"):
    """Take a screenshot and ask the vision model to describe/analyze it."""
    import requests

    filepath, b64 = take_screenshot_raw()
    if filepath is None:
        return b64  # Error message

    try:
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": question,
                "images": [b64]
            }],
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500},
            "keep_alive": "30m"
        }

        r = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
        if r.status_code == 200:
            result = r.json()
            answer = result.get("message", {}).get("content", "").strip()
            # Strip think tags
            import re
            answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL | re.IGNORECASE).strip()
            return answer
        else:
            return f"Vision model error: HTTP {r.status_code}"
    except Exception as e:
        return f"Vision error: {e}"


def find_element_on_screen(description, model="gemma4:e4b"):
    """Use vision model or OCR to find a UI element and return its coordinates."""
    import requests
    import os
    import json
    
    filepath, b64 = take_screenshot_raw()
    if filepath is None:
        return json.dumps({"error": b64})

    vision_mode = os.environ.get("JARVIS_VISION_MODE", "vlm")
    if vision_mode == "ocr":
        try:
            import easyocr
            import numpy as np
            reader = easyocr.Reader(['he', 'en'], gpu=False, verbose=False)
            results = reader.readtext(filepath)
            
            best_match = None
            best_score = 0
            desc_lower = description.lower()
            
            for bbox, text, score in results:
                t_lower = text.lower()
                if desc_lower in t_lower or t_lower in desc_lower:
                    if score > best_score:
                        best_score = score
                        tl, tr, br, bl = bbox
                        cx = int((tl[0] + br[0]) / 2)
                        cy = int((tl[1] + br[1]) / 2)
                        best_match = {"x": cx, "y": cy, "found": True, "element": text}
            
            if best_match:
                return json.dumps(best_match, ensure_ascii=False)
            else:
                return json.dumps({"found": False, "element": "not found via OCR"})
        except ImportError:
            return json.dumps({"error": "EasyOCR is not installed. Please run: pip install easyocr"})
        except Exception as e:
            return json.dumps({"error": f"OCR error: {e}"})

    prompt = f"""Look at this screenshot (1280x720 resolution).
Find the UI element described as: "{description}"
Return ONLY a JSON object with the approximate center coordinates:
{{"x": <number>, "y": <number>, "found": true, "element": "<what you found>"}}
If you cannot find it, return: {{"found": false, "element": "not found"}}
Return ONLY the JSON, nothing else."""

    try:
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": prompt,
                "images": [b64]
            }],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 200},
            "keep_alive": "30m"
        }

        r = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
        if r.status_code == 200:
            result = r.json()
            answer = result.get("message", {}).get("content", "").strip()
            # Strip think tags
            import re
            answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL | re.IGNORECASE).strip()
            # Parse JSON from response
            json_match = re.search(r'\{.*?\}', answer, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return {"error": "Model did not return valid JSON", "raw": answer}
        else:
            return {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════
#  UNIFIED COMPUTER ACTION DISPATCHER
# ═══════════════════════════════════════════

def execute_computer_action(action, params=None):
    """
    Single entry point for all computer control actions.
    
    Supported actions:
      screenshot, click, double_click, right_click,
      type, press_key, hotkey, scroll, move_mouse,
      drag, screen_size, mouse_position,
      analyze_screen, find_element
    """
    if params is None:
        params = {}

    action = action.lower().strip()

    if action == "screenshot":
        filepath, b64 = take_screenshot_raw()
        if filepath:
            return {"filepath": filepath, "image_b64": b64, "message": "Screenshot captured. Analyze the image and output your next action."}
        return {"error": str(b64)}

    elif action == "click":
        return click_at(params.get("x", 0), params.get("y", 0))

    elif action == "double_click":
        return double_click_at(params.get("x", 0), params.get("y", 0))

    elif action == "right_click":
        return right_click_at(params.get("x", 0), params.get("y", 0))

    elif action == "type":
        return type_text(params.get("text", ""))

    elif action == "press_key":
        return press_key(params.get("key", "enter"))

    elif action == "hotkey":
        keys = params.get("keys", [])
        if isinstance(keys, str):
            keys = [k.strip() for k in keys.split("+")]
        return hotkey(*keys)

    elif action == "scroll":
        return scroll_screen(
            params.get("direction", "down"),
            params.get("amount", 3)
        )

    elif action == "move_mouse":
        return move_mouse(params.get("x", 0), params.get("y", 0))

    elif action == "drag":
        return drag_to(
            params.get("x1", 0), params.get("y1", 0),
            params.get("x2", 0), params.get("y2", 0)
        )

    elif action == "screen_size":
        return get_screen_size()

    elif action == "mouse_position":
        return get_mouse_position()

    elif action == "analyze_screen":
        return analyze_screen(
            params.get("question", "Describe what you see on the screen."),
            params.get("model", "gemma4:e4b")
        )

    elif action == "find_element":
        result = find_element_on_screen(
            params.get("description", ""),
            params.get("model", "gemma4:e4b")
        )
        return json.dumps(result, ensure_ascii=False)

    else:
        return f"Unknown computer action: {action}. Available: screenshot, click, double_click, right_click, type, press_key, hotkey, scroll, move_mouse, drag, screen_size, mouse_position, analyze_screen, find_element"


# Cleanup old screenshots (keep last 50)
def cleanup_screenshots():
    try:
        files = sorted(
            [os.path.join(SCREENSHOT_DIR, f) for f in os.listdir(SCREENSHOT_DIR) if f.endswith('.png')],
            key=os.path.getmtime
        )
        if len(files) > 50:
            for f in files[:-50]:
                os.remove(f)
    except:
        pass
