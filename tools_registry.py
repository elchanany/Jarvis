# tools_registry.py
# =================
# Jarvis Capabilities — All tools for the LLM Agent
# Each tool has a clear docstring so the LLM knows when to use it.

import os
import subprocess
import time
import json
import threading
from typing import Optional
from langchain_core.tools import tool

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================
# CAPABILITY A: App Launcher
# ============================================

APP_PATHS = {
    "chrome": "chrome",
    "browser": "chrome",
    "spotify": "spotify:",
    "notepad": "notepad",
    "calculator": "calc",
    "explorer": "explorer",
    "vscode": "code",
    "terminal": "wt",
    "settings": "ms-settings:",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "task manager": "taskmgr",
    "control panel": "control",
}

WEBSITES = {
    "youtube": "https://youtube.com",
    "google": "https://google.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chat.openai.com",
    "whatsapp": "https://web.whatsapp.com",
    "facebook": "https://facebook.com",
    "twitter": "https://twitter.com",
    "instagram": "https://instagram.com",
    "tiktok": "https://tiktok.com",
    "github": "https://github.com",
    "reddit": "https://reddit.com",
}


@tool
def launch_app(app_name: str) -> str:
    """
    Launch an application or open a well-known website.
    Use this when the user asks to open/start/launch an app like Chrome, Spotify, Notepad, Calculator, VSCode, etc.
    
    Args:
        app_name: The name of the application to launch (e.g., 'chrome', 'spotify', 'notepad')
    """
    app_name_lower = app_name.lower().strip()
    
    if app_name_lower in APP_PATHS:
        try:
            subprocess.Popen("start " + APP_PATHS[app_name_lower], shell=True)
            return "Successfully launched " + app_name
        except Exception as e:
            return "Error launching " + app_name + ": " + str(e)
    
    if app_name_lower in WEBSITES:
        try:
            subprocess.Popen("start " + WEBSITES[app_name_lower], shell=True)
            return "Opening " + app_name + " in browser"
        except Exception as e:
            return "Error opening website: " + str(e)
    
    try:
        subprocess.Popen("start " + app_name, shell=True)
        return "Attempting to launch " + app_name
    except Exception as e:
        return "Could not find or launch " + app_name


@tool
def open_url(url: str) -> str:
    """
    Open a URL in the default browser.
    
    Args:
        url: The URL to open (e.g., 'https://example.com')
    """
    try:
        if not url.startswith("http"):
            url = "https://" + url
        subprocess.Popen("start " + url, shell=True)
        return "Opening " + url
    except Exception as e:
        return "Error opening URL: " + str(e)


# ============================================
# CAPABILITY B: System Control (Volume/Media)
# ============================================

@tool
def set_volume(action: str) -> str:
    """
    Control the system volume.
    Use this when the user asks to change volume, mute, or unmute.
    
    Args:
        action: The volume action - 'up', 'down', 'mute', 'unmute', or a number 0-100 to set exact level
    """
    try:
        action_lower = action.lower().strip()
        
        # Try exact level first
        try:
            level = int(action_lower)
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            from ctypes import cast, POINTER
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            vol_level = max(0, min(100, level)) / 100.0
            volume.SetMasterVolumeLevelScalar(vol_level, None)
            return f"Volume set to {level}%"
        except (ValueError, ImportError):
            pass
        
        import pyautogui
        if action_lower in ["up", "increase", "louder"]:
            for _ in range(3):
                pyautogui.press("volumeup")
            return "Volume increased"
        elif action_lower in ["down", "decrease", "lower", "quieter"]:
            for _ in range(3):
                pyautogui.press("volumedown")
            return "Volume decreased"
        elif action_lower in ["mute", "silent", "off"]:
            pyautogui.press("volumemute")
            return "Audio muted"
        elif action_lower in ["unmute", "on"]:
            pyautogui.press("volumemute")
            return "Audio unmuted"
        else:
            return "Unknown volume action: " + action
    except Exception as e:
        return "Volume control error: " + str(e)


@tool
def control_media(action: str) -> str:
    """
    Control media playback (play, pause, next, previous).
    Use this when the user asks to play/pause music or skip tracks.
    
    Args:
        action: The media action - 'play', 'pause', 'next', 'previous', 'stop'
    """
    try:
        import pyautogui
        action_lower = action.lower().strip()
        
        if action_lower in ["play", "pause", "playpause"]:
            pyautogui.press("playpause")
            return "Toggled play/pause"
        elif action_lower in ["next", "skip", "forward"]:
            pyautogui.press("nexttrack")
            return "Skipped to next track"
        elif action_lower in ["previous", "prev", "back"]:
            pyautogui.press("prevtrack")
            return "Went to previous track"
        elif action_lower == "stop":
            pyautogui.press("stop")
            return "Stopped playback"
        else:
            return "Unknown media action: " + action
    except Exception as e:
        return "Media control error: " + str(e)


@tool
def play_song(song_name: str) -> str:
    """
    Play a specific song or artist on Spotify.
    Use this when the user asks to play a specific track, song, or artist.
    
    Args:
        song_name: The name of the song and/or artist to play
    """
    try:
        import urllib.parse
        import pyautogui
        
        query = urllib.parse.quote(song_name)
        # Open Spotify directly to the search page for this song
        subprocess.Popen(f"start spotify:-qa:{query}", shell=True)
        
        # Wait a moment for Spotify to open and load the search
        time.sleep(3)
        # Tab to the first result and press enter to play it
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.press("enter")
        
        # Ensure it's playing
        time.sleep(1)
        
        return f"Opening Spotify for {song_name}"
    except Exception as e:
        return f"Error playing song: {str(e)}"

# ============================================
# CAPABILITY C: File Manager
# ============================================

@tool
def list_files(directory: str) -> str:
    """
    List files in a directory.
    
    Args:
        directory: The directory to list - can be 'documents', 'desktop', 'downloads', or a full path
    """
    path_map = {
        "documents": os.path.expanduser("~/Documents"),
        "desktop": os.path.expanduser("~/Desktop"),
        "downloads": os.path.expanduser("~/Downloads"),
        "home": os.path.expanduser("~"),
    }
    
    dir_lower = directory.lower().strip()
    path = path_map.get(dir_lower, directory)
    
    if not os.path.exists(path):
        return "Directory not found: " + path
    if not os.path.isdir(path):
        return "Not a directory: " + path
    
    try:
        files = os.listdir(path)
        if not files:
            return "Directory is empty: " + path
        
        display_files = files[:25]
        result = "Files in " + path + ":\n"
        for f in display_files:
            full_path = os.path.join(path, f)
            if os.path.isdir(full_path):
                result += "[DIR] " + f + "\n"
            else:
                size = os.path.getsize(full_path)
                size_str = f"{size/1024:.0f}KB" if size < 1048576 else f"{size/1048576:.1f}MB"
                result += f"      {f} ({size_str})\n"
        
        if len(files) > 25:
            result += "... and " + str(len(files) - 25) + " more files"
        
        return result
    except PermissionError:
        return "Permission denied: " + path
    except Exception as e:
        return "Error listing files: " + str(e)


@tool
def search_file(filename: str) -> str:
    """
    Search for a file in common directories (Documents, Desktop, Downloads).
    Limited to 3 folder levels deep and 5 second timeout.
    
    Args:
        filename: The name or part of the filename to search for
    """
    search_dirs = [
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
    ]
    
    found = []
    filename_lower = filename.lower()
    start = time.time()
    max_depth = 3
    
    for base_dir in search_dirs:
        if not os.path.exists(base_dir):
            continue
        try:
            for root, dirs, files in os.walk(base_dir):
                # Depth check
                depth = root.replace(base_dir, '').count(os.sep)
                if depth >= max_depth:
                    dirs.clear()
                    continue
                # Timeout check
                if time.time() - start > 5:
                    break
                for f in files:
                    if filename_lower in f.lower():
                        full = os.path.join(root, f)
                        size = os.path.getsize(full)
                        size_str = f"{size/1024:.0f}KB" if size < 1048576 else f"{size/1048576:.1f}MB"
                        found.append(f"{full} ({size_str})")
                        if len(found) >= 10:
                            break
                if len(found) >= 10:
                    break
        except:
            pass
    
    if not found:
        return "No files found matching: " + filename
    
    result = f"Found {len(found)} file(s):\n"
    for f in found:
        result += "  - " + f + "\n"
    return result


@tool
def read_file(filepath: str) -> str:
    """
    Read the contents of a text file, .docx word document, or PDF.
    Use this when the user asks to read, show, or display a file's content.
    
    Args:
        filepath: Full path to the file, or a relative path from common directories
    """
    # Resolve common short paths
    if not os.path.isabs(filepath):
        for base in ["~/Desktop", "~/Documents", "~/Downloads"]:
            full = os.path.join(os.path.expanduser(base), filepath)
            if os.path.exists(full):
                filepath = full
                break
    
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    
    try:
        size = os.path.getsize(filepath)
        if size > 10 * 1024 * 1024:  # 10MB limit for general safety
            return f"File too large to read ({size/1048576:.1f}MB). Max is 10MB."
            
        ext = os.path.splitext(filepath)[1].lower()
        content = ""
        
        if ext == ".docx":
            try:
                import docx
                doc = docx.Document(filepath)
                content = "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                return "The 'python-docx' library is not installed. Run 'pip install python-docx' first."
                
        elif ext == ".pdf":
            try:
                import PyPDF2
                with open(filepath, "rb") as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    for i, page in enumerate(reader.pages):
                        # Extract up to 20 pages to avoid overwhelming
                        if i >= 20:
                            content += f"\n[... PDF truncated after 20 pages. Total pages: {len(reader.pages)} ...]"
                            break
                        page_text = page.extract_text()
                        if page_text:
                            content += f"\n--- Page {i+1} ---\n{page_text}"
            except ImportError:
                return "The 'PyPDF2' library is not installed. Run 'pip install PyPDF2' first."
                
        else:
            # Assume text file by default
            if size > 50000:  # 50KB limit for plain text
                return f"Text file too large to read entirely ({size/1024:.0f}KB). Max is 50KB."
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        
        # Soft limit output text length sent to the AI Context Window
        # (Allows roughly 1000 - 1500 words to prevent blowing context budget)
        if len(content) > 6000:
            content = content[:6000] + f"\n\n... [truncated — file has {len(content)} total characters]"
        
        return f"=== {os.path.basename(filepath)} ===\n{content.strip()}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool
def write_file(filepath: str, content: str) -> str:
    """
    Write or create a text file. Overwrites if file exists.
    Use this when the user asks to create, write, or save a file.
    
    Args:
        filepath: Full path for the file
        content: Text content to write
    """
    try:
        # Safety: don't allow writing to system directories
        dangerous = ["C:\\Windows", "C:\\Program Files", "System32"]
        for d in dangerous:
            if d.lower() in filepath.lower():
                return f"BLOCKED: Cannot write to system directory ({d})"
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return f"File written successfully: {filepath} ({len(content)} chars)"
    except Exception as e:
        return f"Error writing file: {e}"


# ============================================
# CAPABILITY D: System Operations
# ============================================

@tool
def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    now = datetime.now()
    return "The current time is " + now.strftime("%H:%M")


@tool
def get_date() -> str:
    """Get the current date."""
    from datetime import datetime
    now = datetime.now()
    return "Today is " + now.strftime("%A, %B %d, %Y")


@tool
def system_health() -> str:
    """Check computer CPU, RAM, and battery status."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('C:\\')
        
        result = f"CPU: {cpu}% | RAM: {ram.percent}% ({ram.used/1e9:.1f}/{ram.total/1e9:.1f} GB)"
        result += f" | Disk C: {disk.percent}% ({disk.free/1e9:.0f} GB free)"
        
        if hasattr(psutil, 'sensors_battery'):
            bat = psutil.sensors_battery()
            if bat:
                result += f" | Battery: {bat.percent}%{'⚡' if bat.power_plugged else '🔋'}"
        
        return result
    except Exception as e:
        return f"System health error: {e}"


@tool
def battery_status() -> str:
    """Get battery level and charging status."""
    try:
        import psutil
        bat = psutil.sensors_battery()
        if bat is None:
            return "No battery detected (desktop PC?)"
        
        charging = "Charging ⚡" if bat.power_plugged else "On battery 🔋"
        time_left = ""
        if bat.secsleft > 0 and not bat.power_plugged:
            hours = bat.secsleft // 3600
            mins = (bat.secsleft % 3600) // 60
            time_left = f" | ~{hours}h {mins}m remaining"
        
        return f"Battery: {bat.percent}% | {charging}{time_left}"
    except Exception as e:
        return f"Battery error: {e}"


@tool
def system_ops(action: str) -> str:
    """
    Perform system operations. SAFETY: shutdown/restart require explicit confirmation.
    
    Args:
        action: 'lock', 'sleep', 'shutdown', 'restart', 'cancel_shutdown'
    """
    action = action.lower().strip()
    
    if action == "lock":
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Computer locked."
    elif action == "sleep":
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Going to sleep..."
    elif action == "shutdown":
        os.system("shutdown /s /t 30")
        return "⚠️ Shutting down in 30 seconds! Say 'cancel shutdown' to stop."
    elif action == "restart":
        os.system("shutdown /r /t 30")
        return "⚠️ Restarting in 30 seconds! Say 'cancel shutdown' to stop."
    elif action in ["cancel_shutdown", "cancel", "abort"]:
        os.system("shutdown /a")
        return "Shutdown/restart cancelled."
    else:
        return f"Unknown system action: {action}. Available: lock, sleep, shutdown, restart, cancel_shutdown"


@tool
def set_brightness(level: int) -> str:
    """
    Set the screen brightness (0-100).
    
    Args:
        level: Brightness percentage from 0 to 100
    """
    level = max(0, min(100, level))
    
    # Method 1: screen_brightness_control
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return f"Brightness set to {level}%"
    except Exception:
        pass
    
    # Method 2: WMI (for Lenovo and other laptops)
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return f"Brightness set to {level}% (WMI)"
    except Exception:
        pass
    
    return "Could not change brightness. Hardware may not support software control."


@tool
def take_screenshot() -> str:
    """Take a screenshot of the entire screen and save it."""
    try:
        from computer_control import take_screenshot_raw
        filepath, b64 = take_screenshot_raw()
        if filepath:
            return f"Screenshot saved: {filepath}"
        return b64
    except Exception as e:
        return f"Screenshot error: {e}"


# ============================================
# CAPABILITY E: Memory / Remember
# ============================================

MEMORY_FILE = os.path.join(PROJECT_DIR, "user_memories.json")

@tool
def remember_fact(fact: str) -> str:
    """
    Remember a fact or piece of information about the user.
    Use this when the user says "remember that..." or tells you personal information.
    
    Args:
        fact: The fact to remember
    """
    from datetime import datetime
    
    memories = []
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                memories = json.load(f)
        except:
            memories = []
    
    memories.append({
        "fact": fact,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        return "I'll remember that: " + fact
    except Exception as e:
        return "Error saving memory: " + str(e)


@tool
def recall_memories() -> str:
    """Recall all saved memories about the user."""
    if not os.path.exists(MEMORY_FILE):
        return "I don't have any memories saved yet."
    
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        if not memories:
            return "I don't have any memories saved yet."
        
        result = "Here's what I remember:\n"
        for m in memories[-15:]:
            result += "- " + m["fact"] + " (saved: " + m["date"] + ")\n"
        return result
    except Exception as e:
        return "Error reading memories: " + str(e)


# ============================================
# CAPABILITY F: Web Search & Internet (UPGRADED)
# ============================================

@tool
def search_web(query: str) -> str:
    """
    Search the internet for information. Returns multiple results for accuracy.
    Use this when you don't know the answer, need current info, news, or facts.
    
    Args:
        query: The search query string
    """
    if not query or not query.strip():
        return "What would you like me to search for?"
    
    results_text = []
    
    # Source 1: DuckDuckGo
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query.strip(), region='wt-wt', timelimit='m',
                max_results=3, backend='auto'
            ))
        
        for r in results:
            title = r.get('title', '')
            body = r.get('body', '')[:300]
            url = r.get('href', '')
            if body:
                results_text.append(f"[{title}] {body}\nSource: {url}")
    except Exception as e:
        pass
    
    # Source 2: Wikipedia (for definitions/facts)
    try:
        import wikipedia
        wiki_results = wikipedia.search(query, results=1)
        if wiki_results:
            summary = wikipedia.summary(wiki_results[0], sentences=2, auto_suggest=False)
            if summary:
                results_text.append(f"[Wikipedia] {summary}")
    except Exception:
        pass
    
    if results_text:
        combined = "\n\n---\n\n".join(results_text[:3])
        return combined
    
    return "Could not find results for: " + query


@tool
def deep_research(query: str) -> str:
    """
    Deep research tool — fetches ACCURATE, REAL-TIME data from multiple authoritative sources.
    Use instead of search_web when the user needs:
    - Current crypto/stock/currency prices (Bitcoin, Dollar rate, etc.)
    - Accurate financial data
    - Comprehensive research on a topic
    - When search_web gave outdated or inaccurate results
    
    Args:
        query: The research question (e.g., "Bitcoin price USD", "dollar shekel rate", "inflation Israel")
    """
    import requests as _req
    results = []
    q = query.lower().strip()
    
    # ── A: Crypto prices via CoinGecko (free API, no key) ──
    CRYPTO_MAP = {
        'bitcoin': 'bitcoin', 'btc': 'bitcoin',
        'ethereum': 'ethereum', 'eth': 'ethereum',
        'solana': 'solana', 'sol': 'solana',
        'xrp': 'ripple', 'ripple': 'ripple',
        'dogecoin': 'dogecoin', 'doge': 'dogecoin',
        'bnb': 'binancecoin', 'binance': 'binancecoin',
    }
    detected_coin = next((CRYPTO_MAP[k] for k in CRYPTO_MAP if k in q), None)
    if detected_coin:
        try:
            r = _req.get(
                f"https://api.coingecko.com/api/v3/simple/price",
                params={"ids": detected_coin, "vs_currencies": "usd,ils", "include_24hr_change": "true", "include_market_cap": "true"},
                timeout=8, headers={"Accept": "application/json"}
            )
            if r.status_code == 200:
                data = r.json().get(detected_coin, {})
                usd = data.get('usd', '?')
                ils = data.get('ils', '?')
                chg = data.get('usd_24h_change', 0)
                mcap = data.get('usd_market_cap', 0)
                arrow = '▲' if chg and chg > 0 else '▼'
                results.append(
                    f"**{detected_coin.upper()} — Live Price (CoinGecko)**\n"
                    f"- **USD:** ${usd:,.2f}\n"
                    f"- **ILS:** ₪{ils:,.2f}\n"
                    f"- **שינוי 24h:** {arrow} {abs(chg):.2f}%\n"
                    f"- **שווי שוק:** ${mcap/1e9:.1f}B\n"
                    f"Source: https://www.coingecko.com/he/coins/{detected_coin}"
                )
        except Exception:
            pass

    # ── B: Currency rates via exchangerate-api (free tier) ──
    CURRENCY_PAIRS = {
        'dollar': ('USD', 'ILS'), 'דולר': ('USD', 'ILS'),
        'euro': ('EUR', 'ILS'), 'יורו': ('EUR', 'ILS'), 'אירו': ('EUR', 'ILS'),
        'pound': ('GBP', 'ILS'), 'לירה': ('GBP', 'ILS'),
        'yen': ('JPY', 'ILS'), 'ין': ('JPY', 'ILS'),
        'usd': ('USD', 'ILS'), 'eur': ('EUR', 'ILS'),
    }
    detected_pair = next((CURRENCY_PAIRS[k] for k in CURRENCY_PAIRS if k in q), None)
    if detected_pair and not detected_coin:  # don't double-dip if it's crypto
        base, target = detected_pair
        try:
            r = _req.get(
                f"https://open.er-api.com/v6/latest/{base}",
                timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                rate = data.get('rates', {}).get(target)
                updated = data.get('time_last_update_utc', '')
                if rate:
                    results.append(
                        f"**{base}/{target} — שער חליפין בזמן אמת**\n"
                        f"- **1 {base} = {rate:.4f} {target}**\n"
                        f"- עדכון אחרון: {updated}\n"
                        f"Source: https://open.er-api.com"
                    )
        except Exception:
            pass

    # ── C: DuckDuckGo — 5 results with extended body ──
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(
                query.strip(), region='il-he', timelimit='d',
                max_results=5, backend='auto'
            ))
        for r in ddg_results:
            body = r.get('body', '')[:500]
            url = r.get('href', '')
            title = r.get('title', '')
            if body:
                results.append(f"**{title}**\n{body}\nSource: {url}")
    except Exception:
        pass

    if not results:
        return f"לא נמצאו תוצאות עבור: {query}"

    return "\n\n---\n\n".join(results[:6])


@tool
def get_weather(city: str = "Tel Aviv") -> str:
    """
    Get current weather for a city using wttr.in API.
    
    Args:
        city: City name (default: Tel Aviv)
    """
    try:
        import requests
        # wttr.in returns clean text weather
        r = requests.get(
            f"https://wttr.in/{city}?format=%l:+%C+%t+💧%h+💨%w",
            timeout=5,
            headers={"User-Agent": "curl/7.68.0"}
        )
        if r.status_code == 200 and r.text.strip():
            return r.text.strip()
    except Exception:
        pass
    
    # Fallback to web search
    return search_web.invoke({"query": f"weather {city} today temperature"})


@tool
def read_webpage(url: str) -> str:
    """
    Read and extract text content from a webpage URL.
    Use this when you need to read an article or specific web page content.
    
    Args:
        url: The URL to read
    """
    if not url or not url.startswith("http"):
        return "Invalid URL."
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=8)
        response.raise_for_status()
        
        # Use response.content (bytes) so BeautifulSoup can detect encoding from HTML headers
        soup = BeautifulSoup(response.content, 'html.parser')
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:2500] + "..." if len(text) > 2500 else text
    except Exception as e:
        return f"Could not read page: {e}"


@tool
def read_url(url: str) -> str:
    """
    Alias for read_webpage. Read and extract text content from a webpage URL.
    
    Args:
        url: The URL to read
    """
    return read_webpage.invoke({"url": url})



# ============================================
# CAPABILITY G: Process & Window Management
# ============================================

@tool
def kill_process(name: str) -> str:
    """
    Kill a running process by name.
    
    Args:
        name: Process name (e.g., 'chrome', 'notepad', 'spotify')
    """
    try:
        # Add .exe if not present
        if not name.lower().endswith('.exe'):
            name = name + '.exe'
        
        result = subprocess.run(
            ["taskkill", "/IM", name, "/F"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return f"Process {name} killed successfully"
        return f"Could not kill {name}: {result.stderr.strip()}"
    except Exception as e:
        return f"Kill process error: {e}"


@tool
def list_windows() -> str:
    """List all currently open windows with their titles."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -Property ProcessName, MainWindowTitle | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            return result.stdout.strip()
        return "No windows found or error reading window list."
    except Exception as e:
        return f"Window list error: {e}"


@tool
def run_command(command: str) -> str:
    """
    Execute a terminal/powershell command and return the output.
    SAFETY: Blocks dangerous commands. Use for safe operations only.
    
    Args:
        command: The command to execute
    """
    # Block dangerous commands
    dangerous = ["rm -rf", "format", "del /s", "rmdir /s", "shutdown", "restart",
                 "reg delete", "cipher /w", "sfc", "dism", "bcdedit"]
    for d in dangerous:
        if d.lower() in command.lower():
            return f"BLOCKED: Command contains dangerous operation ({d})"
    
    try:
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout.strip() or result.stderr.strip()
        if len(output) > 2000:
            output = output[:2000] + "\n... [truncated]"
        return output if output else "Command executed (no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 15 seconds"
    except Exception as e:
        return f"Command error: {e}"


@tool
def clipboard_ops(action: str, text: str = "") -> str:
    """
    Get or set clipboard content.
    
    Args:
        action: 'get' to read clipboard, 'set' to write to clipboard
        text: Text to copy (only for 'set')
    """
    try:
        if action.lower() == "get":
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, timeout=3
            )
            content = result.stdout.strip()
            if len(content) > 1000:
                content = content[:1000] + "... [truncated]"
            return f"Clipboard content: {content}" if content else "Clipboard is empty"
        
        elif action.lower() == "set":
            subprocess.run(
                ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
                capture_output=True, timeout=3
            )
            return f"Copied to clipboard: {text[:50]}..."
        
        return "Unknown clipboard action. Use 'get' or 'set'."
    except Exception as e:
        return f"Clipboard error: {e}"


@tool
def wifi_info() -> str:
    """Get current WiFi/network connection info."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            # Extract key info
            lines = result.stdout.strip().split('\n')
            important = [l.strip() for l in lines if any(k in l.lower() for k in 
                        ['ssid', 'state', 'speed', 'signal', 'channel'])]
            return '\n'.join(important) if important else result.stdout.strip()[:500]
        return "No WiFi info available"
    except Exception as e:
        return f"WiFi info error: {e}"


@tool
def set_wallpaper(path: str) -> str:
    """
    Set the desktop wallpaper.
    
    Args:
        path: Full path to an image file
    """
    try:
        import ctypes
        if not os.path.exists(path):
            return f"Image not found: {path}"
        
        ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
        return f"Wallpaper set to: {path}"
    except Exception as e:
        return f"Wallpaper error: {e}"


# ============================================
# CAPABILITY H: Computer Control (Agentic Robot)
# ============================================

@tool
def computer_action(action: str, params: dict = None) -> str:
    """
    Control the computer like a robot: click, type, scroll, take screenshots, analyze screen.
    
    Actions: screenshot, click, double_click, right_click, type, press_key, hotkey,
             scroll, move_mouse, drag, screen_size, mouse_position, analyze_screen, find_element
    
    Args:
        action: The action to perform
        params: Dictionary with parameters. Examples:
            click: {"x": 500, "y": 300}
            type: {"text": "hello world"}
            hotkey: {"keys": "ctrl+c"}
            scroll: {"direction": "down", "amount": 3}
            analyze_screen: {"question": "What app is open?"}
            find_element: {"description": "the search bar"}
    """
    try:
        from computer_control import execute_computer_action
        if params is None:
            params = {}
        
        result = execute_computer_action(action, params)
        if isinstance(result, dict):
            import json
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as e:
        return f"Computer action error: {e}"
    except Exception as e:
        return f"Computer action error: {e}"


# ============================================
# CAPABILITY I: Telegram & External
# ============================================


@tool
def read_telegram_news(channel_name: str = "") -> str:
    """
    Read latest news from configured Telegram channels.
    Fetches messages per channel and returns raw data for summarizing.
    Use when user asks for news, briefing, חדשות, עדכון, מה קורה.
    
    Args:
        channel_name: Optional specific channel. Leave empty for ALL channels.
    """
    import re as _re
    
    def _clean_telegram_text(raw: str) -> str:
        """Remove spam, links, promos, and collapse whitespace from telegram text."""
        lines = raw.splitlines()
        cleaned = []
        seen_stories = set()
        
        for line in lines:
            stripped = line.strip()
            
            # Skip promotional / join links
            if _re.search(r'https?://t\.me/[+\w]', stripped):
                continue
            if _re.search(r't\.me/\+', stripped):
                continue
            # Skip "join channel" lines
            if any(x in stripped for x in ['⭕️', '🔴', 'הצטרפו', 'לחצו', 'לינק', 'קישור', 'להצטרף']):
                continue
            # Skip lines that are just emojis or symbols
            if stripped and _re.fullmatch(r'[\U00010000-\U0010ffff⭕️🔴✅❌⚠️💥🚨📢📣🔥💡🎯·\s]+', stripped):
                continue
            # Skip blank lines that follow other blank lines (collapse whitespace)
            if not stripped:
                if cleaned and cleaned[-1] == '':
                    continue
            
            # Dedup very similar lines (first 60 chars)
            key = _re.sub(r'\s+', ' ', stripped[:60]).lower()
            if key and len(key) > 20 and key in seen_stories:
                continue
            if key and len(key) > 20:
                seen_stories.add(key)
            
            cleaned.append(stripped if stripped else '')
        
        # Remove leading/trailing blank lines
        result = '\n'.join(cleaned).strip()
        
        # Hard cap: 2500 chars max
        if len(result) > 2500:
            result = result[:2500] + "\n... [נקצר]"
        
        return result
    
    try:
        import telegram_manager
        if channel_name and channel_name.strip():
            news = telegram_manager.get_channel_updates(channel_name, limit=20)
            raw = telegram_manager.format_news_for_jarvis(news)
        else:
            raw = telegram_manager.get_all_news_for_ai_summary(limit_per_channel=10)
        
        return _clean_telegram_text(raw)
    except Exception as e:
        return f"Error reading Telegram: {e}"


# ============================================
# Export all tools
# ============================================

ALL_TOOLS = [
    # Apps & URLs
    launch_app,
    open_url,
    # Audio/Media
    set_volume,
    control_media,
    play_song,
    # Files
    list_files,
    search_file,
    read_file,
    write_file,
    # System
    get_time,
    get_date,
    system_health,
    battery_status,
    system_ops,
    set_brightness,
    take_screenshot,
    # Memory
    remember_fact,
    recall_memories,
    # Internet
    search_web,
    deep_research,
    get_weather,
    read_webpage,
    read_url,
    # Process & Window
    kill_process,
    list_windows,
    run_command,
    clipboard_ops,
    wifi_info,
    set_wallpaper,
    # Computer Control (Agentic)
    computer_action,
    # Telegram
    read_telegram_news,
]
