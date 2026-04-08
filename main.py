# Jarvis - Offline AI Assistant
# Full agent with: STT (Whisper/NPU), LLM (Phi-4/GPU), TTS (Kokoro/CPU)
# === FIXED VERSION - Mic stays open inside single with block ===

import os
import sys
import time
import json
import re
import persona
from persona import get_action_response
from tools import search_web, get_time, get_date, get_day, remember_this, find_local_file, play_song
from sounds import (
    sound_startup, sound_shutdown, sound_success,
    start_thinking, start_searching, start_computer_action, stop_loop_sound
)
from intent_classifier import (
    classify_intent, should_ask_clarification, get_clarification_prompt, 
    preprocess_query, validate_result, get_smart_fallback
)

# === LOGGING HELPER ===
def log_model_load(name, device, load_time, success=True):
    status = "✓" if success else "✗"
    print(f"   {status} {name} loaded on {device} in {load_time:.2f}s")

# Force OpenVINO DLLs into PATH
_ov_init_start = time.time()
try:
    import openvino as ov
    ov_path = os.path.dirname(ov.__file__)
    os.environ["PATH"] = ov_path + ";" + os.path.join(ov_path, "libs") + ";" + os.environ["PATH"]
    print(f"🔧 OpenVINO PATH injected ({time.time() - _ov_init_start:.2f}s)")
except ImportError:
    print("⚠️ OpenVINO not found")

import subprocess
import numpy as np
import threading
import queue
import re
import signal
import atexit

# === GRACEFUL SHUTDOWN ===
_shutdown_requested = False
_active_threads = []

def graceful_shutdown(signum=None, frame=None):
    """Handle Ctrl+C gracefully by stopping all threads and cleaning up."""
    global _shutdown_requested
    if _shutdown_requested:
        return  # Prevent multiple calls
    _shutdown_requested = True
    
    print("\n\n🛑 Shutting down gracefully...")
    
    # Stop any playing sounds
    try:
        stop_loop_sound()
    except:
        pass
    
    # Play shutdown sound
    try:
        sound_shutdown()
    except:
        pass
    
    # Give threads time to finish
    for t in _active_threads:
        if t.is_alive():
            t.join(timeout=1.0)
    
    print("✅ Cleanup complete. Goodbye!")
    os._exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, graceful_shutdown)
signal.signal(signal.SIGTERM, graceful_shutdown)
atexit.register(graceful_shutdown)
import pyaudio
import speech_recognition as sr

# === PATHS ===
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
PHI4_PATH = os.path.join(MODELS_DIR, "phi4-mini")
WHISPER_PATH = os.path.join(MODELS_DIR, "whisper-small-he-openvino")
KOKORO_MODEL_PATH = os.path.join(MODELS_DIR, "kokoro-intel", "kokoro-v0_19.onnx")
KOKORO_VOICES_PATH = os.path.join(MODELS_DIR, "kokoro-intel", "voices-v1.0.bin")

# === QUICK COMMANDS ===
QUICK_COMMANDS = {
    # Interrupt commands
    "stop": {"action": "interrupt", "response": ""},
    "silence": {"action": "interrupt", "response": ""},
    "shut up": {"action": "interrupt", "response": ""},
    "be quiet": {"action": "interrupt", "response": ""},
    # Media commands
    "stop music": {"action": "media_stop", "response": "Stopping"},
    "play music": {"action": "media_play", "response": "Playing"},
    "pause": {"action": "media_pause", "response": "Paused"},
    "resume": {"action": "media_play", "response": "Resuming"},
    "next song": {"action": "media_next", "response": "Next"},
    "next": {"action": "media_next", "response": "Next"},
    "previous song": {"action": "media_prev", "response": "Previous"},
    "previous": {"action": "media_prev", "response": "Previous"},
    "volume up": {"action": "volume_up", "response": "Volume up"},
    "volume down": {"action": "volume_down", "response": "Volume down"},
    "mute": {"action": "mute", "response": "Muted"},
    "unmute": {"action": "unmute", "response": "Unmuted"},
    # Browser & Apps
    "open chrome": {"action": "open_app", "app": "chrome", "response": "Opening Chrome"},
    "open browser": {"action": "open_app", "app": "chrome", "response": "Opening browser"},
    "open spotify": {"action": "open_app", "app": "spotify:", "response": "Opening Spotify"},
    "open notepad": {"action": "open_app", "app": "notepad", "response": "Opening Notepad"},
    "open calculator": {"action": "open_app", "app": "calc", "response": "Opening Calculator"},
    "take screenshot": {"action": "screenshot", "response": "Screenshot"},
    "lock screen": {"action": "lock", "response": "Locking"},
    # Websites
    "open youtube": {"action": "open_url", "url": "https://youtube.com", "response": "Opening YouTube"},
    "open tiktok": {"action": "open_url", "url": "https://www.tiktok.com", "response": "Opening TikTok"},
    "open chatgpt": {"action": "open_url", "url": "https://chat.openai.com", "response": "Opening ChatGPT"},
    "open chat gpt": {"action": "open_url", "url": "https://chat.openai.com", "response": "Opening ChatGPT"},
    "open whatsapp": {"action": "open_url", "url": "https://web.whatsapp.com", "response": "Opening WhatsApp"},
    "open gmail": {"action": "open_url", "url": "https://mail.google.com", "response": "Opening Gmail"},
    "open google": {"action": "open_url", "url": "https://www.google.com", "response": "Opening Google"},
    "open facebook": {"action": "open_url", "url": "https://www.facebook.com", "response": "Opening Facebook"},
    "open instagram": {"action": "open_url", "url": "https://www.instagram.com", "response": "Opening Instagram"},
    "open twitter": {"action": "open_url", "url": "https://twitter.com", "response": "Opening Twitter"},
    "open x": {"action": "open_url", "url": "https://twitter.com", "response": "Opening X"},
}

JARVIS_TRIGGERS = ["jarvis", "hey jarvis", "hi jarvis", "okay jarvis", "ג'רוויס", "גרוויס"]

# === GLOBALS ===
whisper_pipeline = None
phi4_pipeline = None
kokoro_engine = None
audio_queue = None
player_thread = None

SAMPLE_RATE = 24000

# === CONFIGURATION (Ready for UI) ===
CONFIG = {
    "voice": "bm_daniel",  # British Daniel - user's choice
    "speed": 1.1,
    "available_voices": [],  # Populated at runtime
}

# For backward compatibility
VOICE_NAME = CONFIG["voice"]

# Interrupt mechanism
is_speaking = False
stop_speaking = threading.Event()

# === SYSTEM PROMPT ===
system_prompt = f"""
SYSTEM INSTRUCTIONS:
You are JARVIS, an AI assistant.
Answer in MAX 1 SENTENCE. Be concise.

--- YOUR IDENTITY (STRICT) ---
Name: Jarvis
Creator: Elchanan
Role: AI Assistant
RESTRICTION: You are NOT the user. You do not have a physical body. 
Do NOT invent life details, job titles, or past events about yourself or the user unless explicitly told.
Stick to verifiable conversational history.

--- DECISION PROTOCOL ---
1. SAFETY CHECK (Shutdown/Restart):
   - "Shut down" -> {{"tool": "system_ops", "params": {{"action": "shutdown"}}}}

2. SYSTEM CONTROL (Volume/Media):
   - "Volume Up" -> {{"tool": "control_volume", "params": {{"action": "up"}}}}
   - "Mute" -> {{"tool": "control_volume", "params": {{"action": "mute"}}}}
   - "Next Song" -> {{"tool": "control_media", "params": {{"action": "next"}}}}

3. PLAY MUSIC ("Play [song] on Spotify/YouTube"):
   - "Play Thunder" -> {{"tool": "play_song", "params": {{"song": "Thunder", "platform": "spotify"}}}}

4. GENERAL KNOWLEDGE / EXPLANATIONS ("Why is...", "Explain...", "How to..."):
   - ANSWER DIRECTLY using your internal knowledge. DO NOT USE TOOLS.
   - Only search if you absolutely do not know the answer.

5. SPECIFIC FACTS / NEWS ("Who is Prime Minister of...", "Weather in..."):
   - Use {{"tool": "search_wikipedia", "params": {{"query": "..."}}}} for definitions.
   - Use {{"tool": "search_web", "params": {{"query": "..."}}}} for news/weather.
   - RESTRICTION: NEVER search for "Me", "User", "You", or "I". Answer these from context only.

6. PERSONAL / TIME / DATE:
   - "Time?" -> {{"tool": "get_time", "params": {{}}}}
   - "Date?" -> {{"tool": "get_date", "params": {{}}}} 
   - "Remember X" -> {{"tool": "remember_this", "params": {{"fact": "..."}}}}

FORMAT: 
- IF USING A TOOL: Output ONLY valid JSON.
- IF CHATTING: Output ONLY PLAIN TEXT.
"""

# === INTERNAL MIC DETECTION ===
def get_intel_internal_mic_index():
    """Find internal Microphone Array to avoid Bluetooth quality drop."""
    p = pyaudio.PyAudio()
    internal_mic_index = None
    
    print("🔍 Scanning for Internal Microphone...")
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        name = dev.get('name', "")
        channels = dev.get('maxInputChannels', 0)
        
        if channels > 0:  # Input device
            # Look for internal mic (Microphone Array or Realtek)
            # Exclude Bluetooth Hands-Free
            if ("Microphone Array" in name or "Realtek" in name) and "Hands-Free" not in name:
                internal_mic_index = i
                print(f"   ✅ Found: {name} (index {i})")
                break
    
    if internal_mic_index is None:
        print("   ⚠️ Internal mic not found, using system default")
    
    p.terminate()
    return internal_mic_index

# === ACTION EXECUTOR ===
def execute_action(action_data):
    action = action_data.get("action")
    try:
        if action == "media_stop":
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]178)"], capture_output=True)
        elif action in ["media_play", "media_pause"]:
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]179)"], capture_output=True)
        elif action == "media_next":
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]176)"], capture_output=True)
        elif action == "media_prev":
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]177)"], capture_output=True)
        elif action == "volume_up":
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"], capture_output=True)
        elif action == "volume_down":
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"], capture_output=True)
        elif action in ["mute", "unmute"]:
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"], capture_output=True)
        elif action == "open_app":
            subprocess.Popen(f"start {action_data.get('app', '')}", shell=True)
        elif action == "open_url":
            subprocess.Popen(f"start {action_data.get('url', '')}", shell=True)
        elif action == "screenshot":
            subprocess.Popen("snippingtool", shell=True)
        elif action == "lock":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif action == "interrupt":
            # Stop TTS immediately
            interrupt_speech()
            print("   ⚡ Speech interrupted")
        return True
    except Exception as e:
        print(f"   Action error: {e}")
        return False

def universal_tool_executor(tool_name: str, params: dict) -> str:
    from tools import get_time, get_date, get_day, control_volume, control_media, system_ops, search_web, search_wikipedia, play_song, window_manager, system_health, mouse_keyboard, set_brightness
    
    try:
        if tool_name == "control_volume":
            return control_volume(params.get("action", "mute"))
        elif tool_name == "control_media":
            return control_media(params.get("action", "play"))
        elif tool_name == "system_ops":
            return system_ops(params.get("action", "lock"), force=True)
        elif tool_name == "get_time":
            return get_time()
        elif tool_name == "get_date":
            return get_date()
        elif tool_name == "search_web":
            return search_web(params.get("query", ""))
        elif tool_name == "open_app":
            app_name = params.get("app")
            if not app_name: return "No app specified."
            execute_action({"action": "open_app", "app": app_name})
            return f"Opened {app_name}"
        elif tool_name == "play_song":
            return play_song(params.get("song"), params.get("platform", "spotify"))
        elif tool_name == "window_manager":
            return window_manager(params.get("action", "minimize_all"))
        elif tool_name == "system_health":
            return system_health()
        elif tool_name == "mouse_keyboard":
            return mouse_keyboard(params.get("action", "scroll_down"))
        elif tool_name == "set_brightness":
            return set_brightness(params.get("level", 50))
        elif tool_name == "list_files":
            from tools_registry import list_files
            return list_files.func(params.get("directory", ""))
        elif tool_name == "search_file":
            from tools_registry import search_file
            return search_file.func(params.get("filename", ""))
        else:
            return execute_agent_tool(tool_name, params)
    except Exception as e:
        return f"Error executing {tool_name}: {e}"

# === MODELS ===
def load_whisper():
    global whisper_pipeline
    import openvino_genai as ov_genai
    
    if not os.path.exists(WHISPER_PATH):
        print(f"❌ Whisper not found at {WHISPER_PATH}")
        return False
    
    print("🎤 Loading Whisper STT...")
    for device in ["NPU", "CPU"]:
        try:
            start = time.time()
            whisper_pipeline = ov_genai.WhisperPipeline(WHISPER_PATH, device=device)
            log_model_load("Whisper", device, time.time() - start)
            return True
        except Exception as e:
            print(f"   {device} failed: {str(e)[:50]}...")
    
    print("   ✗ All devices failed")
    return False

def load_phi4():
    global phi4_pipeline
    import openvino_genai as ov_genai
    
    if not os.path.exists(PHI4_PATH):
        print(f"⚠️ Phi-4 not found - LLM disabled")
        return False
    
    print("🧠 Loading Phi-4 LLM...")
    for device in ["GPU", "CPU"]:
        try:
            start = time.time()
            # Enable caching
            config = {"CACHE_DIR": "./model_cache"}
            # Pass config as kwargs (unpacking) to avoid deprecation warning
            phi4_pipeline = ov_genai.LLMPipeline(PHI4_PATH, device=device, **config)
            log_model_load("Phi-4", device, time.time() - start)
            return True
        except Exception as e:
            print(f"   {device} failed: {str(e)[:50]}...")
    
    print("   ✗ All devices failed")
    return False

def load_kokoro():
    global kokoro_engine, audio_queue, player_thread
    
    print("🔊 Loading Kokoro TTS...")
    
    if not os.path.exists(KOKORO_MODEL_PATH):
        print(f"   ⚠️ Model not found")
        return False
    
    try:
        from kokoro_onnx import Kokoro
        import sounddevice as sd
        
        start = time.time()
        kokoro_engine = Kokoro(KOKORO_MODEL_PATH, KOKORO_VOICES_PATH)
        log_model_load("Kokoro TTS", "CPU", time.time() - start)
        
        # Warmup
        print("   🔥 Warming up TTS...")
        _, _ = kokoro_engine.create("Hello", voice=VOICE_NAME, speed=1.0)
        print("   ✓ Warmup complete")
        
        # Audio player thread
        audio_queue = queue.Queue()
        
        def audio_player_worker():
            global is_speaking
            stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            stream.start()
            while True:
                try:
                    audio = audio_queue.get()
                    if audio is None:
                        is_speaking = False
                        break
                    
                    if not stop_speaking.is_set():
                        is_speaking = True
                        stream.write(audio.astype(np.float32))
                    
                    # If queue is empty, we are done speaking for now
                    if audio_queue.empty():
                        is_speaking = False
                        
                    audio_queue.task_done()
                except Exception as e:
                    print(f"Audio worker error: {e}")
                    is_speaking = False
            stream.stop()
            stream.close()
        
        player_thread = threading.Thread(target=audio_player_worker, daemon=True)
        player_thread.start()
        
        return True
    except ImportError:
        print("   ⚠️ kokoro-onnx not installed")
        return False
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        return False

# === TRANSCRIPTION ===
def transcribe(audio_data):
    if whisper_pipeline is None:
        return ""
    
    try:
        start = time.time()
        raw_bytes = audio_data.get_raw_data(convert_rate=16000, convert_width=2)
        audio_array = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        
        if np.max(np.abs(audio_array)) < 0.01:
            return ""
        
        result = whisper_pipeline.generate(audio_array, language="<|en|>")
        
        text = ""
        if hasattr(result, 'texts') and result.texts:
            text = result.texts[0]
        elif hasattr(result, 'text'):
            text = result.text
        else:
            text = str(result)
        
        elapsed = time.time() - start
        clean_text = text.strip().lower()
        if clean_text:
            print(f"   📝 STT: {elapsed*1000:.0f}ms")
        
        return clean_text
    except Exception as e:
        print(f"   STT error: {e}")
        return ""

# === TTS ===
def split_into_chunks(text):
    chunks = re.split(r'(?<=[,;:.!?])\s+', text)
    result = []
    current = ""
    for chunk in chunks:
        if len(current) + len(chunk) < 40:
            current = (current + " " + chunk).strip()
        else:
            if current:
                result.append(current)
            current = chunk
    if current:
        result.append(current)
    return result if result else [text]

def speak(text):
    global is_speaking
    
    if kokoro_engine is None or audio_queue is None:
        try:
            subprocess.run(["powershell", "-Command", f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'], capture_output=True, timeout=30)
        except:
            pass
        return
    
    stop_speaking.clear()
    is_speaking = True
    start_time = time.time()
    
    chunks = split_into_chunks(text)
    first_audio_time = None
    total_audio_duration = 0
    
    audio_queue.put(np.zeros(int(SAMPLE_RATE * 0.1), dtype=np.float32))
    
    for chunk in chunks:
        if not chunk.strip() or stop_speaking.is_set():
            break
        
        audio, sr = kokoro_engine.create(chunk, voice=VOICE_NAME, speed=1.1)
        
        if first_audio_time is None:
            first_audio_time = time.time() - start_time
            print(f"   ⚡ First: {first_audio_time*1000:.0f}ms")
        
        total_audio_duration += len(audio) / sr
        audio_queue.put(audio)
    
    audio_queue.put(np.zeros(int(SAMPLE_RATE * 0.3), dtype=np.float32))
    
    # Non-blocking: We don't wait for audio to finish
    # audio_queue.join() 
    
    # is_speaking is now managed by audio_player_worker
    
    print(f"   🗣️ Speaking (non-blocking)...")

def speak_stream(text_iterator):
    global is_speaking
    
    if kokoro_engine is None or audio_queue is None:
        full = "".join(text_iterator)
        speak(full)
        return
    
    stop_speaking.clear()
    is_speaking = True
    start_time = time.time()
    first_audio_time = None
    total_audio_duration = 0
    
    buffer = ""
    print("🔊 ", end="", flush=True)
    
    audio_queue.put(np.zeros(int(SAMPLE_RATE * 0.1), dtype=np.float32))
    
    for token in text_iterator:
        if stop_speaking.is_set():
            break
        
        print(token, end="", flush=True)
        buffer += token
        
        if re.search(r'[.!?]\s*$', buffer) or (len(buffer) > 50 and re.search(r'[,:;]\s*$', buffer)):
            chunk = buffer.strip()
            buffer = ""
            
            if chunk:
                audio, sr = kokoro_engine.create(chunk, voice=VOICE_NAME, speed=1.1)
                
                if first_audio_time is None:
                    first_audio_time = time.time() - start_time
                    print(f"\n   ⚡ First: {first_audio_time*1000:.0f}ms", end="")
                
                total_audio_duration += len(audio) / sr
                audio_queue.put(audio)
    
    if buffer.strip() and not stop_speaking.is_set():
        audio, sr = kokoro_engine.create(buffer.strip(), voice=VOICE_NAME, speed=1.0)
        total_audio_duration += len(audio) / sr
        audio_queue.put(audio)
    
    print()
    audio_queue.put(np.zeros(int(SAMPLE_RATE * 0.3), dtype=np.float32))
    
    # Non-blocking: We don't wait for audio to finish
    # audio_queue.join() 
    
    # is_speaking is now managed by audio_player_worker
    
    print(f"   🗣️ Speaking stream (non-blocking)...")

def interrupt_speech():
    stop_speaking.set()
    if audio_queue:
        try:
            while not audio_queue.empty():
                audio_queue.get_nowait()
                audio_queue.task_done()
        except:
            pass

# === AGENT (LLM + Tools) ===
def parse_tool_call(response: str) -> tuple:
    """Check if response is a tool call. Returns (tool_name, params) or (None, None)."""
    import json
    
    # Look for JSON in response
    try:
        # Try to find JSON object in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            json_str = response[start:end]
            data = json.loads(json_str)
            if "tool" in data:
                return data.get("tool"), data.get("params", {})
    except:
        pass
    
    return None, None

def execute_agent_tool(tool_name: str, params: dict) -> str:
    """
    Execute a tool safely - handles hallucinated parameters.
    Uses inspect.signature to check what the function actually accepts.
    """
    import inspect
    from tools import TOOLS
    from memory import MEMORY_TOOLS
    
    # Find the tool
    tool_info = None
    if tool_name in TOOLS:
        tool_info = TOOLS[tool_name]
    elif tool_name in MEMORY_TOOLS:
        tool_info = MEMORY_TOOLS[tool_name]
    
    if not tool_info:
        return f"Unknown tool: {tool_name}"
    
    func = tool_info["function"]
    
    try:
        # Check function signature
        sig = inspect.signature(func)
        expected_params = list(sig.parameters.keys())
        
        if len(expected_params) == 0:
            # Function takes NO parameters - ignore any hallucinated params
            print(f"   🔧 {tool_name}() - no params needed")
            return func()
        else:
            # Filter params to only those the function accepts
            clean_params = {}
            for key, value in params.items():
                if key in expected_params and key != "none":
                    clean_params[key] = value
            
            print(f"   🔧 {tool_name}({clean_params})")
            return func(**clean_params)
    except Exception as e:
        return f"Tool error: {str(e)}"

def chat_with_jarvis_stream(user_message, callback):
    """
    Agent loop: LLM decides to respond or call tools.
    FIXED: Don't speak while generating - collect first, then decide.
    """
    if phi4_pipeline is None:
        callback("Brain not loaded.")
        return
    
    import persona
    from tools import (
        search_web, get_time, get_date, get_day, remember_this, find_local_file, open_url,
        control_volume, control_media, system_ops, search_wikipedia
    )
    
    # 1. DECISION TREE System Prompt 
    user_context = persona.get_user_context() 
    
    # (Prompt moved to global scope)
    pass

    prompt = f"{system_prompt}\n\nUser: {user_message}\nJarvis:"
    
    try:
        start = time.time()
        # Stream response
        print(f"\n   🧠 LLM Thinking...", end="", flush=True)
        
        # Start thinking sound
        try:
            from sounds import start_thinking, stop_loop_sound
            start_thinking()
        except:
            pass

        # OpenVINO GenAI Generation
        response_buffer = phi4_pipeline.generate(prompt, max_new_tokens=200)
        
        if not isinstance(response_buffer, str):
            response_buffer = str(response_buffer)

        print(f"\r   🧠 LLM: {time.time() - start:.2f}s")
        
        # Stop thinking sound
        try:
            stop_loop_sound()
        except:
            pass
        
        # 1. New Robust Tool Detection Logic
        final_speech_text = response_buffer.strip()
        tool_executed = False
        
        # DEBUG: Print raw LLM Output
        print(f"   📜 RAW LLM: {response_buffer[:100]}...")

        # Pre-clean: Remove Markdown Code Blocks for Phi-4 behavior
        cleaned_response = re.sub(r'```json\s*', '', response_buffer, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'```\s*', '', cleaned_response)
        # NOTE: DO NOT replace {{ or }} here - it breaks nested JSON like {"params": {}}

        # Better JSON Extraction: Brace Counting (handles nested {})
        json_str = None
        start_idx = cleaned_response.find('{')
        if start_idx != -1:
            brace_count = 0
            for i, char in enumerate(cleaned_response[start_idx:], start=start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = cleaned_response[start_idx:i+1]
                        break

        if json_str:
            try:
                # DEBUG
                print(f"   🔍 JSON STR: {json_str[:80]}")
                command = None
                
                # 2. Strategy A: Standard JSON
                try:
                    command = json.loads(json_str)
                    print(f"   ✅ JSON OK: {command}") # DEBUG
                except Exception as je:
                    print(f"   ⚠️ JSON FAIL: {je}") # DEBUG
                    
                # 3. Strategy B: Python Literal Eval
                if not command:
                    try:
                        import ast
                        command = ast.literal_eval(json_str)
                        print(f"   ✅ AST OK: {command}") # DEBUG
                    except Exception as ae:
                        print(f"   ⚠️ AST FAIL: {ae}") # DEBUG
                
                # 4. Strategy C: The "Fixer" (Aggressive Repair)
                if not command:
                    try:
                        # Fix single quotes
                        fixed_str = json_str.replace("'", '"')
                        # Fix trailing commas
                        fixed_str = re.sub(r",\s*}", "}", fixed_str)
                        fixed_str = re.sub(r",\s*]", "]", fixed_str)
                        command = json.loads(fixed_str)
                        print(f"   ✅ FIXED OK: {command}") # DEBUG
                    except Exception as fe:
                        print(f"   ⚠️ FIX FAIL: {fe}") # DEBUG

                if command:
                    tool_name = command.get("tool") or list(command.keys())[0] 
                    params = command.get("params", command.get(tool_name))
                    
                    # Stop thinking sound
                    stop_loop_sound()
                    
                    # Start appropriate action sound BEFORE execution
                    # These sounds only play if action takes > 0.2 seconds
                    if tool_name in ["search_web", "search_wikipedia", "read_web_page"]:
                        start_searching()  # Search sound (has built-in delay)
                    elif tool_name == "play_song":
                        start_computer_action()  # Computer action sound
                    # NOTE: Fast actions (volume, media, remember) don't need sounds
                        
                    print(f"🔧 TOOL DETECTED: {tool_name}")
                    
                    # Tool Execution
                    tool_result = ""
                    
                    if tool_name == "control_volume":
                        action = params.get("action")
                        tool_result = control_volume(action)
                        final_speech_text = tool_result
                        
                    elif tool_name == "control_media":
                        action = params.get("action")
                        tool_result = control_media(action)
                        final_speech_text = tool_result
                        
                    elif tool_name == "system_ops":
                        action = params.get("action")
                        # ⚠️ SAFETY CHECK
                        result = system_ops(action, force=False)
                        if result == "REQUIRES_CONFIRMATION":
                            final_speech_text = f"Are you sure you want to {action}? Say 'Yes' to confirm."
                        else:
                            final_speech_text = result
                            
                    elif tool_name == "search_wikipedia":
                        query = params.get("query")
                        tool_result = search_wikipedia(query)
                        if not tool_result:
                            tool_result = "No Wikipedia page found."
                        final_speech_text = tool_result

                    elif tool_name == "get_time":
                        tool_result = get_time()
                        final_speech_text = f"It is {tool_result}."
                    elif tool_name == "get_date":
                        tool_result = get_date()
                        final_speech_text = f"Today is {tool_result}."
                    elif tool_name == "get_day":
                        tool_result = get_day()
                        final_speech_text = f"Today is {tool_result}."
                        
                    elif tool_name == "search_web":
                        query = params.get("query") or "news"
                        tool_result = search_web(str(query))
                        if tool_result == "BROWSER_FALLBACK":
                            final_speech_text = "Search is currently blocked."
                        else:
                            # Result already contains the summary, just speak it
                            final_speech_text = tool_result
                        
                    elif tool_name == "remember_this":
                        fact = params.get("fact")
                        if fact:
                            tool_result = remember_this(str(fact))
                            final_speech_text = "Saved."
                        else:
                            final_speech_text = "Nothing to save."
                    
                    else:
                         # Fallback for other tools
                         tool_result = execute_agent_tool(tool_name, params)
                         final_speech_text = f"Done. {tool_result}"

                    print(f"✅ RESULT: {tool_result}")
                    tool_executed = True

            except Exception as e:
                print(f"❌ JSON PARSE FAILED: {str(e)}")
                final_speech_text = cleaned_response.split("{")[0]

        if "{" in final_speech_text:
            final_speech_text = final_speech_text.split("{")[0]

        if final_speech_text.strip():
            print(f"🔊 Speaking: {final_speech_text[:60]}...")
            callback(final_speech_text)

        print(f"   🧠 LLM: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        try:
            from sounds import stop_loop_sound
            stop_loop_sound()
        except:
            pass
        callback("Sorry, something went wrong.")

# === COMMAND DETECTION ===
def check_quick_command(text):
    text_lower = text.lower()
    for trigger, data in QUICK_COMMANDS.items():
        if trigger in text_lower:
            return data
    return None

def check_jarvis_trigger(text):
    text_lower = text.lower()
    for trigger in JARVIS_TRIGGERS:
        if trigger in text_lower:
            return True
    return False

# === LLM RESPONSE GENERATOR ===
def generate_action_response(action: str, details: str = "") -> str:
    """
    Ask LLM to generate a natural, short response for an action.
    """
    if not phi4_pipeline:
        return f"OK, {action.replace('_', ' ')} {details}"
        
    prompt = f"""<|system|>You are Jarvis.
The user asked you to perform an action: "{action}" ({details}).
You have successfully completed this action.
Generate a very short, natural, and varied confirmation response (under 10 words).
Do not say "Action completed" or "Done". Be conversational, maybe slightly witty.
<|user|>Action: {action} {details}
<|assistant|>"""
    
    try:
        # Generate varied response
        response = phi4_pipeline.generate(prompt, max_new_tokens=25, do_sample=True, temperature=0.8)
        # Extract text if needed (depends on pipeline output format)
        text = response.text if hasattr(response, 'text') else str(response)
        
        return text.strip().replace('"', '')
    except Exception as e:
        print(f"   ⚠️ LLM Gen Error: {e}")
        return "Done."

# === MAIN LOOP ===
def run_jarvis():
    print("\n" + "=" * 60)
    print("       🤖 JARVIS - Offline AI Assistant")
    print("=" * 60)
    
    total_load_start = time.time()
    
    # Find internal mic
    mic_index = get_intel_internal_mic_index()
    
    # Load models
    print("\n📦 Loading Models...")
    
    if not load_whisper():
        print("❌ Cannot start without STT!")
        return
    
    load_phi4()
    load_kokoro()
    
    print(f"\n✅ All models loaded in {time.time() - total_load_start:.2f}s")
    
    # Create recognizer and microphone
    recognizer = sr.Recognizer()
    # Aggressive manual threshold to block background noise
    recognizer.energy_threshold = 300  # WAS 1000 - Lowered for better sensitivity
    recognizer.dynamic_energy_threshold = False # Keep False to prevent adapting to TTS
    # INCREASED: Wait 1.5 seconds of silence before cutting off (was 1.0)
    recognizer.pause_threshold = 1.2
    # Non-speaking audio allowed at start/end (in seconds)
    recognizer.non_speaking_duration = 0.5
    microphone = sr.Microphone(device_index=mic_index)
    
    print("\n" + "=" * 60)
    print("📢 Say 'JARVIS' or speak directly")
    print("=" * 60)
    
    try:
        # CRITICAL: Keep mic open throughout entire session
        with microphone as source:
            print("\n🎤 Calibrating microphone (FAST)...")
            # Minimal adjustment since we set high manual threshold
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            print("✅ Ready! Listening...\n")
            
            # Play startup sound
            try:
                from sounds import sound_startup
                sound_startup()
            except:
                pass
            
            speak("Ready")
            
            # State tracking for Reality Gate
            last_tts_end_time = 0
            was_speaking = False
            
            # === SPEED TEST MODE LOOP (Direct Chat) ===
            print("\n⚡ SPEED TEST MODE (Direct Chat)")
            print("Listening for voice input...")
            
            # State tracking for Reality Gate
            last_tts_end_time = 0
            was_speaking = False
            
            while True:
                text_input = ""
                
                try:
                    # 1. Listen for Audio
                    # DYNAMIC THRESHOLDING
                    if is_speaking:
                         recognizer.energy_threshold = 1000
                         print("👂", end="", flush=True)
                    else:
                         recognizer.energy_threshold = 300
                         print(".", end="", flush=True)

                    # Listen
                    try:
                        audio = recognizer.listen(source, phrase_time_limit=10, timeout=1.0)
                    except sr.WaitTimeoutError:
                        audio = None
                    
                    # Update Reality Gate timer
                    if was_speaking and not is_speaking:
                         last_tts_end_time = time.time()
                    was_speaking = is_speaking
                    
                    if not audio:
                        continue

                    # Barge-in check
                    if is_speaking:
                         print("\n   ⚡ Barge-in detected!")
                         interrupt_speech()
                         time.sleep(0.2)
                         
                    # Transcribe
                    text_input = transcribe(audio)
                    
                except Exception as e:
                    # print(f"Listen error: {e}")
                    pass
                    
                # 2. Logic: If we have text, send to LLM directly
                if text_input:
                     # REALITY GATE
                     time_since_tts = time.time() - last_tts_end_time
                     if time_since_tts < 0.8:
                          print(f"   🛡️ Reality Gate: Ignored phantom '{text_input}' ({time_since_tts:.2f}s)")
                          continue
                          
                     print(f"\n🎤 User: {text_input}")
                     
                     # === REAL SYSTEM ROUTING ===
                     try:
                         from jarvis_layers import layered_process
                         
                         def local_llm_invoke(prompt_text):
                             if not phi4_pipeline:
                                 return "Brain offline."
                             # Simple wrapper
                             response = phi4_pipeline.generate(prompt_text, max_new_tokens=100)
                             if not isinstance(response, str):
                                 response = str(response.text if hasattr(response, 'text') else response)
                             return response

                         final_res = layered_process(
                             user_input=text_input,
                             llm_invoke=local_llm_invoke,
                             tool_executor=universal_tool_executor,
                             last_action=None
                         )
                         
                         if final_res:
                             speak_stream([final_res])
                             
                     except Exception as e:
                         print(f"   ❌ Pipeline Error: {e}")
                     
                     try:
                         from sounds import stop_loop_sound
                         stop_loop_sound()
                     except:
                         pass
                     print()
                     
                # Update loop state
                if was_speaking and not is_speaking:
                     last_tts_end_time = time.time()
                was_speaking = is_speaking
                    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        try:
            from sounds import sound_shutdown
            sound_shutdown()
        except:
            pass
        speak("Goodbye")
    finally:
        if audio_queue:
            audio_queue.put(None)

def main():
    run_jarvis()

if __name__ == "__main__":
    main()