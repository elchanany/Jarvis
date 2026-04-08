"""
Jarvis Tools - SAFE VERSION with truncation for TTS
"""
import os
import subprocess
import datetime
import json
from typing import Optional

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# === WEB SEARCH (SAFE) ===
def search_web(query: str) -> str:
    """Search the web - SHORT results for TTS."""
    if not query or not query.strip():
        return "What would you like me to search for?"
    
    print(f"   🕵️ Searching: {query}")
    
    try:
        # Use the new ddgs package
        from ddgs import DDGS
        
        # 1. Try DuckDuckGo
        try:
            with DDGS() as ddgs:
                # backend='auto' is the new standard
                results = list(ddgs.text(
                    query.strip(),
                    region='wt-wt',
                    timelimit='d',
                    max_results=1,
                    backend='auto'
                ))
            
            if results:
                r = results[0]
                # Return ONLY the body text (no URL for TTS)
                body = r.get('body', '')[:200]
                return body if body else "I found something but couldn't read it."
                
        except Exception as ddg_error:
            print(f"   ⚠️ DDG Failed ({ddg_error}). Switching to Wikipedia...")

        # 2. Fallback to Wikipedia (Explicit)
        import wikipedia
        # Search for page match
        search_res = wikipedia.search(query, results=1)
        if search_res:
             # Get summary of first result (2 sentences max)
             summary = wikipedia.summary(search_res[0], sentences=2)
             return f"According to Wikipedia: {summary}"
        else:
             return "I couldn't find any results on Wikipedia."
            
    except Exception as e:
        print(f"   ❌ Search System Error: {e}")
        # Final Fallback: Browser
        return "BROWSER_FALLBACK"

def read_web_page(url: str) -> str:
    """Scrape text from a webpage."""
    if not url or not url.startswith("http"):
        return "Invalid URL."
        
    print(f"   🌐 Reading: {url}")
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Kill all script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit length
        return text[:2000] + "..." if len(text) > 2000 else text
        
    except Exception as e:
        return f"Could not read page: {e}"

# --- SYSTEM CONTROL TOOLS ---

def control_volume(action: str) -> str:
    """Controls system volume using keyboard simulation."""
    try:
        import pyautogui
        
        if action == "up":
            pyautogui.press('volumeup')
            pyautogui.press('volumeup')  # Double for noticeable change
            return "Volume increased."
        elif action == "down":
            pyautogui.press('volumedown')
            pyautogui.press('volumedown')
            return "Volume decreased."
        elif action == "mute":
            pyautogui.press('volumemute')
            return "Toggled mute."
        elif action == "unmute":
            pyautogui.press('volumemute')
            return "Toggled mute."
        elif action == "set_50":
            # Can't set specific level with keys, just unmute
            pyautogui.press('volumemute')
            pyautogui.press('volumemute')
            return "Volume adjusted."
            
        return "Unknown volume action."
    except Exception as e:
        return f"Volume Error: {e}"

def control_media(action: str) -> str:
    """Controls media: 'playpause', 'next', 'prev', 'stop'."""
    try:
        import pyautogui
        # Keys: 'playpause', 'nexttrack', 'prevtrack', 'volumemute', etc.
        key_map = {
            "play": "playpause",
            "pause": "playpause",
            "next": "nexttrack",
            "prev": "prevtrack",
            "stop": "stop"
        }
        
        key = key_map.get(action, action)
        pyautogui.press(key)
        return f"Media command '{action}' sent."
    except Exception as e:
        return f"Media Error: {e}"

def system_ops(action: str, force: bool = False) -> str:
    """Handle system operations. Returns 'REQUIRES_CONFIRMATION' if needed."""
    action = action.lower()
    
    if action in ["shutdown", "restart"] and not force:
        return "REQUIRES_CONFIRMATION"
        
    import os
    if action == "shutdown":
        os.system("shutdown /s /t 10")
        return "Shutting down in 10 seconds."
    elif action == "restart":
        os.system("shutdown /r /t 10")
        return "Restarting in 10 seconds."
    elif action == "lock":
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Workstation locked."
    
    return "Unknown system operation."

def search_wikipedia(query: str) -> str:
    """Explicit Wikipedia search for definitions."""
    if not query or not query.strip():
        return ""
    
    # Clean the query - remove filler words
    clean_query = query.strip()
    for filler in ["what is", "who is", "meaning of", "define", "the"]:
        clean_query = clean_query.replace(filler, "").strip()
    
    if not clean_query:
        clean_query = query.strip()
    
    print(f"   📖 Wikipedia query: '{clean_query}'")
        
    try:
        import wikipedia
        wikipedia.set_lang("en")
        
        # Strategy 1: Search first, then get summary (most accurate)
        try:
            results = wikipedia.search(clean_query, results=3)
            print(f"   📚 Found: {results}")
            if results:
                # Pick the best match (first result)
                summary = wikipedia.summary(results[0], sentences=2, auto_suggest=False)
                return summary
        except wikipedia.DisambiguationError as e:
            # Multiple options - pick the first one
            if e.options:
                summary = wikipedia.summary(e.options[0], sentences=2, auto_suggest=False)
                return summary
        except wikipedia.PageError:
            pass
            
        # Strategy 2: Direct query (fallback)
        try:
            summary = wikipedia.summary(clean_query, sentences=2, auto_suggest=False)
            return summary
        except:
            pass
                
        return ""
    except Exception as e:
        print(f"   ⚠️ Wikipedia error: {e}")
        return ""

def get_weather(city: str = "Tel Aviv") -> str:
    """Get weather."""
    return search_web(f"weather {city} today temperature")

def get_time() -> str:
    """Get current time ONLY (Natural format)."""
    # lstrip('0') removes leading zero from hour
    return datetime.datetime.now().strftime('%I:%M %p').lstrip('0')

def get_date() -> str:
    """Get current date ONLY."""
    return datetime.datetime.now().strftime('%B %d, %Y')

def get_day() -> str:
    """Get current day of the week."""
    return datetime.datetime.now().strftime('%A')

# === COMPUTER CONTROL ===
def set_volume(level: int) -> str:
    """Set system volume (0-100)."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        from ctypes import cast, POINTER
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        vol_level = max(0, min(100, level)) / 100.0
        volume.SetMasterVolumeLevelScalar(vol_level, None)
        return f"Volume set to {level} percent"
    except:
        return "Could not change volume"

def open_app(name: str) -> str:
    """Open an application."""
    apps = {
        "chrome": "chrome", "browser": "chrome", "firefox": "firefox",
        "spotify": "spotify:", "notepad": "notepad", "calculator": "calc",
        "settings": "ms-settings:", "vscode": "code", "explorer": "explorer",
        "terminal": "wt", "cmd": "cmd",
    }
    app_cmd = apps.get(name.lower(), name)
    try:
        subprocess.Popen(f"start {app_cmd}", shell=True)
        return f"Opening {name}"
    except:
        return f"Could not open {name}"

def open_url(url: str) -> str:
    """Open a URL."""
    try:
        subprocess.Popen(f"start {url}", shell=True)
        return f"Opening the link"
    except:
        return "Could not open the link"

def media_control(action: str) -> str:
    """Control media playback."""
    key_map = {"play": 179, "pause": 179, "stop": 178, "next": 176, "previous": 177}
    key_code = key_map.get(action.lower())
    if not key_code:
        return f"Unknown action: {action}"
    try:
        subprocess.run(["powershell", "-Command",
            f"(New-Object -ComObject WScript.Shell).SendKeys([char]{key_code})"],
            capture_output=True)
        return f"Media {action}"
    except:
        return "Media control failed"

def take_screenshot() -> str:
    """Take a screenshot."""
    try:
        subprocess.Popen("snippingtool", shell=True)
        return "Screenshot tool opened"
    except:
        return "Could not open screenshot"

def lock_screen() -> str:
    """Lock the computer."""
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        return "Locking screen"
    except:
        return "Could not lock"

def set_brightness(level: int) -> str:
    """Set screen brightness (0-100)."""
    try:
        import screen_brightness_control as sbc
        vol_level = max(0, min(100, level))
        sbc.set_brightness(vol_level)
        return f"Brightness set to {vol_level}%"
    except Exception as e:
        return f"Could not change brightness: {e}"

def window_manager(action: str) -> str:
    """Manage windows: minimize_all, close_current."""
    try:
        import pyautogui
        if action == "minimize_all":
            pyautogui.hotkey('win', 'd') # Show desktop
            return "All windows minimized."
        elif action == "close_current":
            pyautogui.hotkey('alt', 'f4')
            return "Current window closed."
        return "Unknown window action."
    except Exception as e:
        return f"Window manager error: {e}"

def system_health() -> str:
    """Get CPU and RAM load."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        return f"System load: CPU is at {cpu} percent, and Memory is at {ram} percent."
    except:
        return "Could not read system health. Psutil not installed."

def mouse_keyboard(action: str) -> str:
    """Basic keyboard/mouse macros: scroll_down, scroll_up, enter."""
    try:
        import pyautogui
        if action == "scroll_down":
            pyautogui.scroll(-500)
            return "Scrolled down."
        elif action == "scroll_up":
            pyautogui.scroll(500)
            return "Scrolled up."
        elif action == "enter":
            pyautogui.press('enter')
            return "Pressed enter."
        return "Unknown macro."
    except:
        return "Macro failed."

def find_local_file(filename: str) -> str:
    """Find a file on computer."""
    if not filename or not filename.strip():
        return "What file should I look for?"
    
    print(f"   📂 Searching for: {filename}")
    search_paths = [
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
    ]
    found = []
    for base in search_paths:
        if not os.path.exists(base):
            continue
        for root, dirs, files in os.walk(base):
            for f in files:
                if filename.lower() in f.lower():
                    found.append(f)
                    if len(found) >= 3:
                        break
            if len(found) >= 3:
                break
    
    if found:
        return f"Found: {', '.join(found[:3])}"
    return f"Could not find {filename}"

# === MEMORY ===
def remember_this(fact: str) -> str:
    """Save to long-term memory."""
    if not fact or not fact.strip():
        return "What should I remember?"
    
    try:
        data_file = os.path.join(PROJECT_DIR, "user_data.json")
        
        if not os.path.exists(data_file):
            data = {"profile": {}, "dynamic_memory": []}
        else:
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        if "dynamic_memory" not in data:
            data["dynamic_memory"] = []
        
        data["dynamic_memory"].append({
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "fact": fact.strip()
        })
        
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return f"I'll remember: {fact[:50]}"
    except Exception as e:
        return "Could not save to memory"

# === PLAY SONG ===
def play_song(song: str, platform: str = "spotify") -> str:
    """Play a song on Spotify or YouTube by opening search URL."""
    if not song or not song.strip():
        return "What song should I play?"
    
    song_query = song.strip().replace(" ", "+")
    platform = platform.lower() if platform else "spotify"
    
    try:
        if platform in ["youtube", "yt"]:
            url = f"https://www.youtube.com/results?search_query={song_query}"
            subprocess.Popen(f"start {url}", shell=True)
            return f"Searching YouTube for {song}"
        else:  # Default to Spotify
            # Spotify search URL (quoted)
            url = f'spotify:search:"{song.strip()}"'
            subprocess.Popen(f"start {url}", shell=True)
            return f"Opening Spotify for {song}"
    except Exception as e:
        return f"Could not play song: {e}"

# === TOOL REGISTRY ===
TOOLS = {
    "search_web": {"function": search_web, "description": "Search internet", "parameters": ["query"]},
    "get_weather": {"function": get_weather, "description": "Get weather", "parameters": ["city"]},
    "get_time": {"function": get_time, "description": "Get time", "parameters": []},
    "set_volume": {"function": set_volume, "description": "Set volume", "parameters": ["level"]},
    "open_app": {"function": open_app, "description": "Open app", "parameters": ["name"]},
    "open_url": {"function": open_url, "description": "Open URL", "parameters": ["url"]},
    "media_control": {"function": media_control, "description": "Media control", "parameters": ["action"]},
    "find_local_file": {"function": find_local_file, "description": "Find file", "parameters": ["filename"]},
    "take_screenshot": {"function": take_screenshot, "description": "Screenshot", "parameters": []},
    "lock_screen": {"function": lock_screen, "description": "Lock", "parameters": []},
    "remember_this": {"function": remember_this, "description": "Save memory", "parameters": ["fact"]},
    "play_song": {"function": play_song, "description": "Play song on Spotify/YouTube", "parameters": ["song", "platform"]},
    "set_brightness": {"function": set_brightness, "description": "Set screen brightness", "parameters": ["level"]},
    "window_manager": {"function": window_manager, "description": "Manage windows", "parameters": ["action"]},
    "system_health": {"function": system_health, "description": "Check CPU and RAM", "parameters": []},
    "mouse_keyboard": {"function": mouse_keyboard, "description": "Keyboard macros", "parameters": ["action"]},
}

def execute_tool(tool_name: str, **kwargs) -> str:
    """Execute a tool."""
    if tool_name not in TOOLS:
        return f"Unknown tool: {tool_name}"
    try:
        return TOOLS[tool_name]["function"](**kwargs)
    except Exception as e:
        return f"Tool error: {str(e)}"

def get_tools_description() -> str:
    """Get tools list for LLM."""
    desc = "Tools:\n"
    for name, info in TOOLS.items():
        params = ", ".join(info["parameters"]) if info["parameters"] else "none"
        desc += f"- {name}({params})\n"
    return desc
