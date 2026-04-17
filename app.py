import os
import glob
import base64
from flask import Flask, render_template, request, Response, jsonify, send_from_directory
import json
import datetime
import time
import threading
import queue
import requests as http_requests
import psutil
from requests.adapters import HTTPAdapter
ollama_session = http_requests.Session()
# Configure pooling
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=10)
ollama_session.mount('http://', adapter)
from dotenv import load_dotenv

# Load `.env` into environment variables
load_dotenv()

import sys
from collections import deque

# Noise patterns to filter from in-app terminal (still go to real stdout)
_TERMINAL_NOISE = (
    '"GET /api/load-status',
    '"GET /api/loaded-models',
    '"GET /api/ollama-status',
    '"GET /api/models',
    '"GET /api/logs/poll',
    '"GET /static/',
    '"GET /api/conversations',
    '"GET /favicon',
    '304 -',
    '200 -',
)

class LogBuffer:
    """Captures stdout/stderr into a ring buffer for the in-app terminal overlay.
    Filters out repetitive API polling noise to keep the terminal readable."""
    def __init__(self):
        self.q = deque(maxlen=500)
        self._orig_stdout = sys.__stdout__
        self.encoding = 'utf-8'
        self.q.append("[JARVIS LOG CORE] Terminal attached successfully.\n")
    def write(self, text):
        if text:
            # Normalize to str (Flask/click sometimes sends bytes)
            if isinstance(text, bytes):
                try:
                    text = text.decode('utf-8', errors='replace')
                except Exception:
                    text = str(text)
            # Always write to real stdout
            try:
                if self._orig_stdout:
                    self._orig_stdout.write(text)
            except Exception:
                pass
            # Only add to UI buffer if not noise
            text_str = str(text)
            if not any(noise in text_str for noise in _TERMINAL_NOISE):
                self.q.append(text_str)
    def flush(self):
        try:
            if self._orig_stdout:
                self._orig_stdout.flush()
        except Exception:
            pass

log_buffer = LogBuffer()
sys.stdout = log_buffer
sys.stderr = log_buffer

from gemma_brain import run_gemma_chat_stream, parse_gemma_response, prompt_config, generate_system_prompt
from tools_registry import ALL_TOOLS
from conversations import (
    create_conversation, list_conversations, get_conversation,
    save_messages, rename_conversation, delete_conversation, auto_title
)

# Load jarvis configuration locally if it exists
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis_config.json")
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Override initial prompt_config from JSON
            if "persona" in cfg: prompt_config["persona"] = cfg["persona"]
            if "style" in cfg: prompt_config["style"] = cfg["style"]
            if "rules" in cfg: prompt_config["rules"] = cfg["rules"]
    except Exception as e:
        print(f"[JARVIS] Failed to load {CONFIG_FILE}: {e}")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_UPLOAD_DIR = os.path.join(PROJECT_DIR, "uploads", "audio")
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)

# Background task: Cleanup audio older than 24h
def cleanup_old_audio():
    while True:
        now = time.time()
        for f in glob.glob(os.path.join(AUDIO_UPLOAD_DIR, "*.webm")):
            if os.path.isfile(f) and os.stat(f).st_mtime < now - 24 * 3600:
                try:
                    os.remove(f)
                except Exception:
                    pass
        time.sleep(3600)  # check every hour

threading.Thread(target=cleanup_old_audio, daemon=True).start()

OLLAMA_BASE = "http://127.0.0.1:11434"

import subprocess

def start_ollama_if_needed():
    try:
        ollama_session.get(OLLAMA_BASE + "/", timeout=1)
    except Exception:
        print("\n[JARVIS] Ollama is not running. Starting Ollama automatically...")
        try:
            # CREATE_NO_WINDOW = 0x08000000 inside subprocess on Windows
            creationflags = 0x08000000 if os.name == 'nt' else 0
            subprocess.Popen(
                ["ollama", "serve"],
                creationflags=creationflags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Poll for readiness
            for _ in range(8):
                try:
                    time.sleep(1)
                    ollama_session.get(OLLAMA_BASE + "/", timeout=1)
                    print("[JARVIS] Ollama started successfully!\n")
                    return
                except Exception:
                    pass
        except Exception as e:
            print(f"[JARVIS] Failed to auto-start Ollama: {e}\n")

threading.Thread(target=start_ollama_if_needed, daemon=True).start()

# ═══════════════════════════════════════════
#  KEEP-ALIVE PING — prevent model unloading
# ═══════════════════════════════════════════
_last_model_load_time = 0  # timestamp of last model load/chat

def resource_watchdog():
    """Monitor system RAM. Only unload if CRITICALLY low (>93%) AND model has been idle for 5+ minutes.
    Intel Arc shares system RAM, so 75-90% usage is NORMAL with a loaded model."""
    import sys
    while True:
        time.sleep(60)  # check every 60s instead of 30s
        try:
            # Don't unload during generation
            if getattr(sys.modules[__name__], 'is_generating', False):
                continue
            
            # Don't unload within 5 minutes of last load/chat
            if time.time() - _last_model_load_time < 300:
                continue
                
            mem_usage = psutil.virtual_memory().percent
            if mem_usage > 93.0:  # Only at CRITICAL pressure (was 85%)
                r = ollama_session.get(f"{OLLAMA_BASE}/api/ps", timeout=5)
                if r.status_code == 200:
                    loaded = r.json().get("models", [])
                    if loaded:
                        print(f"\n[⚠️ WATCHDOG] Critical Memory Pressure ({mem_usage}% RAM). Unloading model.")
                        for m in loaded:
                            ollama_session.post(f"{OLLAMA_BASE}/api/generate", json={
                                "model": m["name"], "keep_alive": 0
                            }, timeout=10)
        except Exception:
            pass

# Start the watchdog
threading.Thread(target=resource_watchdog, daemon=True).start()

def keepalive_ping():
    """Ping Ollama every 4 minutes with a minimal request to keep the model loaded in VRAM."""
    import time as _time
    _time.sleep(30)  # wait for initial startup
    while True:
        try:
            # Just ask the model to stay loaded with keep_alive (without changing context/options to avoid reloading)
            ollama_session.post(f"{OLLAMA_BASE}/api/generate", json={
                "model": "gemma4:e4b",
                "keep_alive": "30m"
            }, timeout=10)
        except:
            pass
        _time.sleep(240)  # every 4 minutes

threading.Thread(target=keepalive_ping, daemon=True).start()

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Force no caching — pywebview's Edge backend caches aggressively
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Current active conversation
active_conv = {"id": None, "history": []}

# Build a fast name-to-tool lookup dict from registry
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}

def execute_parsed_tool(command_dict):
    if not command_dict: return None
    tool_name = command_dict.get("tool")
    args = command_dict.get("args", {})
    if not tool_name or tool_name == "null" or not isinstance(tool_name, str):
        return "No tool name provided."
    print(f"\n[🔌 SYSTEM] Executing: {tool_name}({args})")
    
    # Route through the real tools registry
    if tool_name in _TOOL_MAP:
        try:
            return str(_TOOL_MAP[tool_name].invoke(args))
        except Exception as e:
            return f"Tool error [{tool_name}]: {e}"
    
    # Fallback for get_time (in case it's missing from registry for some reason)
    if tool_name == "get_time":
        return datetime.datetime.now().strftime("The current time is %H:%M")
    
    return f"Tool '{tool_name}' not found."

# ═══════════════════════════════════════════
#  MODEL MANAGEMENT
# ═══════════════════════════════════════════

@app.route("/api/ollama-status")
def ollama_status():
    try:
        ollama_session.get(f"{OLLAMA_BASE}/", timeout=3)
        return jsonify({"online": True})
    except:
        return jsonify({"online": False})

@app.route("/api/models")
def list_models_route():
    try:
        r = ollama_session.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        if r.status_code == 200:
            models = []
            for m in r.json().get("models", []):
                size_bytes = m.get("size", 0)
                details = m.get("details", {})
                models.append({
                    "name": m["name"],
                    "size_gb": round(size_bytes / 1e9, 1),
                    "params": details.get("parameter_size", "?"),
                    "family": details.get("family", "?"),
                    "quant": details.get("quantization_level", "?"),
                    "modified": m.get("modified_at", "")[:10],
                })
            return jsonify({"models": models})
        return jsonify({"models": []})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})

@app.route("/api/loaded-models")
def loaded_models():
    try:
        r = ollama_session.get(f"{OLLAMA_BASE}/api/ps", timeout=5)
        if r.status_code == 200:
            loaded = []
            for m in r.json().get("models", []):
                raw_size = m.get("size", 0)
                raw_vram = m.get("size_vram", raw_size)
                loaded.append({
                    "name": m.get("name", m.get("model", "?")),
                    "size_gb": round(raw_size / (1024**3), 1) if raw_size else 0,
                    "vram_gb": round(raw_vram / (1024**3), 1) if raw_vram else 0,
                    "processor": m.get("details", {}).get("processor", "CPU"),
                    "expires": m.get("expires_at", ""),
                })
            return jsonify({"loaded": loaded})
        return jsonify({"loaded": []})
    except Exception as e:
        return jsonify({"loaded": [], "error": str(e)})

# Global load/unload state tracker (persists across page refreshes)
model_load_state = {
    "active": False,
    "action": None,      # "load" or "unload"
    "model": None,
    "started_at": None,
    "completed": False,
    "success": None,
    "error": None,
    "load_time": None,
}

def _bg_load_model(model_name):
    """Background worker for loading a model — lightweight preload.
    
    Uses minimal num_ctx (2048) and num_predict (1) to load weights into
    VRAM without triggering 'memory layout cannot be allocated' errors
    on Intel Arc / Vulkan backends.
    """
    global model_load_state, _last_model_load_time
    _last_model_load_time = time.time()
    print(f"\n[⏳ LOAD] Starting background load of {model_name}...")
    try:
        # Minimal preload: tiny context + single token prediction
        # This loads the model weights without allocating a huge KV cache
        r = ollama_session.post(f"{OLLAMA_BASE}/api/generate", json={
            "model": model_name,
            "prompt": "",
            "keep_alive": "30m",
            "options": {
                "num_ctx": 2048,
                "num_predict": 1
            }
        }, timeout=(10, 300))
        
        elapsed = round(time.time() - model_load_state["started_at"], 1)
        if r.status_code == 200:
            _last_model_load_time = time.time()
            print(f"[✅ LOAD] {model_name} weights loaded in {elapsed}s")
            model_load_state.update({"completed": True, "success": True, "load_time": elapsed, "error": None})
        else:
            # Fallback: try show-only (doesn't allocate KV cache at all)
            print(f"[⚠️ LOAD] generate failed ({r.status_code}), trying show fallback...")
            r2 = ollama_session.post(f"{OLLAMA_BASE}/api/show", json={"model": model_name}, timeout=30)
            elapsed = round(time.time() - model_load_state["started_at"], 1)
            if r2.status_code == 200:
                print(f"[✅ LOAD] {model_name} verified via show in {elapsed}s (will load on first chat)")
                model_load_state.update({"completed": True, "success": True, "load_time": elapsed, "error": None})
            else:
                print(f"[❌ LOAD] {model_name} failed: status {r.status_code}")
                model_load_state.update({"completed": True, "success": False, "error": f"HTTP {r.status_code}: memory layout error — model will load on first chat", "load_time": elapsed})
    except Exception as e:
        elapsed = round(time.time() - (model_load_state.get("started_at") or time.time()), 1)
        print(f"[❌ LOAD] {model_name} error after {elapsed}s: {e}")
        model_load_state.update({"completed": True, "success": False, "error": str(e), "load_time": elapsed})

def _bg_unload_model(model_name):
    """Background worker for unloading a model."""
    global model_load_state
    try:
        r = ollama_session.post(f"{OLLAMA_BASE}/api/generate", json={
            "model": model_name, 
            "prompt": "",
            "keep_alive": 0
        }, timeout=30)
        elapsed = round(time.time() - model_load_state["started_at"], 1)
        model_load_state.update({"completed": True, "success": r.status_code == 200, "load_time": elapsed, "error": None})
    except Exception as e:
        elapsed = round(time.time() - model_load_state["started_at"], 1)
        model_load_state.update({"completed": True, "success": False, "error": str(e), "load_time": elapsed})

@app.route("/api/load-model", methods=["POST"])
def load_model():
    try:
        global model_load_state
        req = request.get_json(silent=True) or {}
        model = req.get("model", "gemma4:e4b")
        
        # If already loading, return the current state
        if model_load_state["active"] and not model_load_state["completed"]:
            elapsed = round(time.time() - (model_load_state["started_at"] or time.time()), 1)
            return jsonify({"already_running": True, "model": model_load_state["model"], "elapsed": elapsed})
        
        # Start background load
        model_load_state = {
            "active": True, "action": "load", "model": model,
            "started_at": time.time(), "completed": False,
            "success": None, "error": None, "load_time": None,
        }
        threading.Thread(target=_bg_load_model, args=(model,), daemon=True).start()
        return jsonify({"started": True, "model": model})
    except Exception as e:
        import traceback
        err = traceback.format_exc()
        print(f"[API ERROR] load-model crashed: {err}")
        return jsonify({"started": False, "error": str(e)}), 500

@app.route("/api/unload-model", methods=["POST"])
def unload_model():
    global model_load_state
    req = request.json or {}
    model = req.get("model", "gemma4:e4b")
    
    model_load_state = {
        "active": True, "action": "unload", "model": model,
        "started_at": time.time(), "completed": False,
        "success": None, "error": None, "load_time": None,
    }
    threading.Thread(target=_bg_unload_model, args=(model,), daemon=True).start()
    return jsonify({"started": True, "model": model})

@app.route("/api/load-status")
def load_status():
    """Returns current load/unload operation state. Frontend polls this."""
    if not model_load_state["active"]:
        return jsonify({"active": False})
    
    elapsed = round(time.time() - model_load_state["started_at"], 1) if model_load_state["started_at"] else 0
    
    # Safety timeout: 600s (Vulkan model loading can take 5+ minutes)
    if not model_load_state["completed"] and elapsed > 600:
        model_load_state.update({
            "completed": True, "success": False,
            "error": f"Timeout after {elapsed}s — Ollama might be stuck", "load_time": elapsed
        })
        print(f"[⚠️ LOAD] Force-timeout after {elapsed}s")
    
    return jsonify({
        "active": True,
        "action": model_load_state["action"],
        "model": model_load_state["model"],
        "elapsed": elapsed,
        "completed": model_load_state["completed"],
        "success": model_load_state["success"],
        "error": model_load_state["error"],
        "load_time": model_load_state["load_time"],
    })

# ═══════════════════════════════════════════
#  ABORT & STATE
# ═══════════════════════════════════════════
@app.route("/api/terminal/input", methods=["POST"])
def terminal_input():
    req = request.json or {}
    cmd = req.get("command", "").strip()
    if not cmd:
        return jsonify({"success": False})
    
    print(f"\n> {cmd}")
    
    def run_cmd():
        try:
            # We use shell=True so things like 'dir' or 'echo' work natively
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
            for line in iter(proc.stdout.readline, ''):
                sys.stdout.write(line)
            proc.stdout.close()
            proc.wait()
        except Exception as e:
            print(f"[CMD ERROR] {e}")
            
    threading.Thread(target=run_cmd, daemon=True).start()
    return jsonify({"success": True})
active_generation = {"abort": threading.Event(), "thread": None}
is_generating = False
is_generating = False

@app.route("/api/abort", methods=["POST"])
def abort_generation():
    active_generation["abort"].set()
    return jsonify({"success": True})

# ═══════════════════════════════════════════
#  SETTINGS API
# ═══════════════════════════════════════════

@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(prompt_config)

@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.json
    if "persona" in data: prompt_config["persona"] = data["persona"]
    if "style" in data: prompt_config["style"] = data["style"]
    if "rules" in data: prompt_config["rules"] = data["rules"]
    full = generate_system_prompt()
    est_tokens = len(full) // 3
    return jsonify({"success": True, "prompt_length": len(full), "est_tokens": est_tokens})

@app.route("/api/config", methods=["GET"])
def get_global_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except: pass
        
    return jsonify({
        "config": cfg,
        "env": {
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
            "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
        }
    })

@app.route("/api/config", methods=["POST"])
def save_global_config():
    data = request.json
    cfg_data = data.get("config", {})
    env_data = data.get("env", {})
    
    # Save config
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, ensure_ascii=False, indent=2)
            
        # Update live prompt_config if needed
        if "persona" in cfg_data: prompt_config["persona"] = cfg_data["persona"]
        if "style" in cfg_data: prompt_config["style"] = cfg_data["style"]
        if "rules" in cfg_data: prompt_config["rules"] = cfg_data["rules"]
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

    # Save ENV secrets securely using python-dotenv (or fallback to overwriting)
    try:
        from dotenv import set_key
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if not os.path.exists(env_file):
            open(env_file, 'w').close()
            
        for k, v in env_data.items():
            if v:
                set_key(env_file, k, v)
                os.environ[k] = v
    except Exception as e:
        pass
        
    return jsonify({"success": True})

# ═══════════════════════════════════════════
#  CONVERSATIONS API
# ═══════════════════════════════════════════

@app.route("/api/conversations", methods=["GET"])
def api_list_conversations():
    return jsonify({"conversations": list_conversations()})

@app.route("/api/conversations", methods=["POST"])
def api_create_conversation():
    conv = create_conversation()
    active_conv["id"] = conv["id"]
    active_conv["history"] = []
    return jsonify(conv)

@app.route("/api/conversations/<cid>", methods=["GET"])
def api_get_conversation(cid):
    conv = get_conversation(cid)
    if not conv:
        return jsonify({"error": "not found"}), 404
    active_conv["id"] = cid
    active_conv["history"] = conv["messages"]
    return jsonify(conv)

@app.route("/api/conversations/<cid>", methods=["PUT"])
def api_rename_conversation(cid):
    title = request.json.get("title", "")
    rename_conversation(cid, title)
    return jsonify({"success": True})

@app.route("/api/conversations/<cid>", methods=["DELETE"])
def api_delete_conversation(cid):
    delete_conversation(cid)
    if active_conv["id"] == cid:
        active_conv["id"] = None
        active_conv["history"] = []
    return jsonify({"success": True})

# ═══════════════════════════════════════════
#  MAIN ROUTES
# ═══════════════════════════════════════════

@app.route("/api/transcribe_and_save", methods=["POST"])
def transcribe_and_save():
    """Receive Base64 audio blob, save to disk for WhatsApp-like UI, AND transcribe.
    Supports two STT modes: 'whisper' (local Whisper-HE) or 'gemma' (Gemma4 native audio).
    """
    data = request.json
    audio_b64 = data.get("audio_b64", "")
    model = data.get("model", "gemma4:e4b")
    stt_mode = data.get("stt_mode", "whisper")  # 'whisper' or 'gemma'
    
    if not audio_b64:
        return jsonify({"error": "No audio data provided"}), 400
    
    try:
        # 1. Decode and Save to disk
        audio_data = base64.b64decode(audio_b64)
        filename = f"voice_{int(time.time()*1000)}.webm"
        file_path = os.path.join(AUDIO_UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as f:
            f.write(audio_data)
            
        audio_url = f"/audio/{filename}"
        print(f"[AUDIO] Saved {filename} ({len(audio_data)//1024}KB) — mode: {stt_mode}")
        
        # 2. Transcribe
        transcript = ""
        
        if stt_mode == "whisper":
            # Use local Whisper-HE (OpenVINO) — 100% offline!
            try:
                import stt_engine
                transcript = stt_engine.transcribe_audio_b64(audio_b64, language="he")
            except Exception as e:
                print(f"[STT] Whisper failed: {e}, falling back to Gemma4")
                stt_mode = "gemma"  # Fallback
        
        if stt_mode == "gemma" or (stt_mode == "whisper" and not transcript):
            # Use Gemma4 native audio understanding
            payload = {
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": "Transcribe this audio recording exactly as spoken. Print ONLY the transcribed text. No translations, no extra words, no explanations.",
                    "images": [audio_b64]
                }],
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 4096,
                    "num_predict": 1024
                },
                "keep_alive": "30m"
            }
            
            r = ollama_session.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
            
            if r.status_code == 200:
                result = r.json()
                transcript = result.get("message", {}).get("content", "").strip()
                import re as _re
                transcript = _re.sub(r'<think>.*?</think>', '', transcript, flags=_re.DOTALL | _re.IGNORECASE).strip()
            else:
                print(f"[AUDIO] Gemma4 returned {r.status_code}")
        
        if transcript:
            print(f"[AUDIO] ✅ Transcript: {transcript[:80]}")
        else:
            print(f"[AUDIO] ⚠️ No transcript produced")
        
        return jsonify({"url": audio_url, "transcript": transcript})
            
    except Exception as e:
        print(f"[AUDIO] ❌ Error: {e}")
        return jsonify({"error": str(e), "url": "", "transcript": ""}), 500

@app.route("/api/stt", methods=["POST"])
def api_stt():
    """Quick STT endpoint for voice call mode — local Whisper only, returns text fast."""
    data = request.json
    audio_b64 = data.get("audio_b64", "")
    
    if not audio_b64:
        return jsonify({"text": ""}), 400
    
    try:
        import stt_engine
        text = stt_engine.transcribe_audio_b64(audio_b64, language="he")
        return jsonify({"text": text})
    except Exception as e:
        print(f"[STT API] Error: {e}")
        return jsonify({"text": "", "error": str(e)}), 500

@app.route("/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_UPLOAD_DIR, filename)

@app.route("/api/logs/poll")
def poll_logs():
    """Fallback polling endpoint for terminal logs (when SSE doesn't work in pywebview)."""
    try:
        # Safely copy the list before iterating to avoid 'deque mutated during iteration'
        items = list(log_buffer.q)
        logs_str = "".join([str(item) for item in items])
        return jsonify({"logs": logs_str})
    except Exception as e:
        return jsonify({"logs": f"Server Error reading logs: {e}"})

# ═══════════════════════════════════════════
#  FIRST-RUN SETUP DETECTION
# ═══════════════════════════════════════════
SETUP_DONE_FILE = os.path.join(PROJECT_DIR, ".setup_complete")

def get_hardware_specs():
    """Detect hardware and recommend the best model for this machine."""
    try:
        import psutil, subprocess
        ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
        
        gpu_name = "לא ידוע"
        try:
            proc = subprocess.run(["wmic", "path", "win32_VideoController", "get", "name"], capture_output=True, text=True, timeout=3)
            lines = [l.strip() for l in proc.stdout.split('\n') if l.strip() and "Name" not in l]
            if lines: gpu_name = " + ".join(lines)
        except: pass
        
        cpu_name = "לא ידוע"
        try:
            proc = subprocess.run(["wmic", "cpu", "get", "name"], capture_output=True, text=True, timeout=3)
            lines = [l.strip() for l in proc.stdout.split('\n') if l.strip() and "Name" not in l]
            if lines: cpu_name = lines[0]
        except: pass
        
        # Smart model recommendation based on RAM
        if ram_gb >= 24:
            rec_model = "gemma2:27b"
            rec_name = "Gemma 2 27B"
            rec_size = "~16GB"
            rec_reason = "יש לך מספיק זיכרון למודל החזק ביותר"
        elif ram_gb >= 12:
            rec_model = "gemma2:9b"
            rec_name = "Gemma 2 9B"
            rec_size = "~5.5GB"
            rec_reason = "איזון מושלם בין מהירות לאיכות עבור המחשב שלך"
        else:
            rec_model = "gemma2:2b"
            rec_name = "Gemma 2 2B"
            rec_size = "~1.6GB"
            rec_reason = "קל ומהיר, מותאם לזיכרון המוגבל שלך"
        
        return {
            "ram": f"{ram_gb}GB",
            "ram_gb": ram_gb,
            "gpu": gpu_name,
            "cpu": cpu_name,
            "rec_model": rec_model,
            "rec_name": rec_name,
            "rec_size": rec_size,
            "rec_reason": rec_reason,
        }
    except:
        return {
            "ram": "לא ידוע", "ram_gb": 0, "gpu": "לא ידוע", "cpu": "לא ידוע",
            "rec_model": "gemma2:9b", "rec_name": "Gemma 2 9B",
            "rec_size": "~5.5GB", "rec_reason": "ברירת מחדל מומלצת",
        }

def is_setup_needed():
    """Returns True if first-time setup is required."""
    if os.path.exists(SETUP_DONE_FILE):
        return False
    
    # Check if models exist locally without relying on active API
    home = os.path.expanduser("~")
    models_dir = os.path.join(home, ".ollama", "models", "manifests", "registry.ollama.ai", "library")
    if os.path.exists(models_dir):
        # User has downloaded some models
        has_gemma = any('gemma' in d for d in os.listdir(models_dir) if os.path.isdir(os.path.join(models_dir, d)))
        if has_gemma:
            return False
            
    try:
        r = ollama_session.get(OLLAMA_BASE + "/api/tags", timeout=2)
        models = r.json().get("models", [])
        return len(models) == 0
    except Exception:
        return True
@app.route("/")
def index():
    if is_setup_needed():
        specs = get_hardware_specs()
        return render_template("setup.html", specs=specs)
    return render_template("index.html")


# ─── Setup: streaming dependency install ───
@app.route("/setup/install", methods=["POST"])
def setup_install():
    def generate():
        import subprocess, shutil
        def send(d):
            return f"data: {json.dumps(d, ensure_ascii=False)}\n\n"
        
        # Step 1: Python check
        yield send({"type":"step","step":"step-python","state":"active","badge":"בודק..."})
        import sys
        ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        yield send({"type":"log","text":f"Python {ver} נמצא ✓","cls":"t-ok"})
        yield send({"type":"step","step":"step-python","state":"done","badge":f"Python {ver}"})
        
        # Step 2: Install pip deps — check first, install only if needed
        yield send({"type":"step","step":"step-deps","state":"active","badge":"בודק..."})
        
        # Quick check: try importing critical packages
        deps_ok = True
        try:
            import importlib
            for pkg in ['flask', 'requests', 'psutil', 'langchain_core', 'PIL', 'bs4', 'duckduckgo_search']:
                importlib.import_module(pkg)
        except ImportError:
            deps_ok = False
        
        if deps_ok:
            yield send({"type":"log","text":"כל הספריות כבר מותקנות ✓","cls":"t-ok"})
            yield send({"type":"step","step":"step-deps","state":"done","badge":"מותקן ✓"})
        else:
            yield send({"type":"log","text":"מתקין ספריות חסרות..."})
            req_file = os.path.join(PROJECT_DIR, "requirements.txt")
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            for line in proc.stdout:
                line = line.strip()
                if line and not line.startswith('WARNING'):
                    yield send({"type":"log","text":line,"cls":"t-ok" if "Successfully" in line else ""})
            proc.wait()
            if proc.returncode == 0:
                yield send({"type":"step","step":"step-deps","state":"done","badge":"מותקן ✓"})
            else:
                yield send({"type":"step","step":"step-deps","state":"error","badge":"שגיאה ✗"})
        
        # Step 3: Ollama check
        yield send({"type":"step","step":"step-ollama","state":"active","badge":"בודק..."})
        ollama_path = shutil.which("ollama")
        if ollama_path:
            yield send({"type":"log","text":f"Ollama נמצא: {ollama_path}","cls":"t-ok"})
            yield send({"type":"step","step":"step-ollama","state":"done","badge":"מותקן ✓"})
        else:
            yield send({"type":"log","text":"Ollama לא מותקן — מוריד...","cls":"t-warn"})
            # Download & install Ollama on Windows
            ollama_installer = os.path.join(PROJECT_DIR, "OllamaSetup.exe")
            try:
                r = ollama_session.get("https://ollama.com/download/OllamaSetup.exe", stream=True, timeout=60)
                with open(ollama_installer, "wb") as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                subprocess.run([ollama_installer, "/S"], check=True)
                yield send({"type":"log","text":"Ollama הותקן בהצלחה!","cls":"t-ok"})
                yield send({"type":"step","step":"step-ollama","state":"done","badge":"הותקן ✓"})
                start_ollama_if_needed()
            except Exception as e:
                yield send({"type":"log","text":f"שגיאה: {e}","cls":"t-err"})
                yield send({"type":"log","text":"⚠ אנא התקן Ollama ידנית: https://ollama.com","cls":"t-warn"})
                yield send({"type":"step","step":"step-ollama","state":"error","badge":"שגיאה"})
        
        # Move to model selection phase
        yield send({"type":"phase","phase":"phase-model"})
    
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


# ─── Setup: pull model with progress ───
@app.route("/setup/pull-model", methods=["POST"])
def setup_pull_model():
    model = request.json.get("model", "gemma4:e4b")
    
    def generate():
        def send(d):
            return f"data: {json.dumps(d, ensure_ascii=False)}\n\n"
        try:
            r = ollama_session.post(
                OLLAMA_BASE + "/api/pull",
                json={"name": model},
                stream=True, timeout=600
            )
            total = 0
            completed = 0
            for line in r.iter_lines():
                if not line: continue
                try:
                    d = json.loads(line)
                    status = d.get("status","")
                    tot = d.get("total", 0)
                    comp = d.get("completed", 0)
                    if tot: total = tot
                    if comp: completed = comp
                    pct = (completed / total * 100) if total > 0 else 0
                    size_mb = f"{completed/1024/1024:.0f}MB / {total/1024/1024:.0f}MB" if total else status
                    yield send({"type":"progress","percent":pct,"label":f"{status} — {size_mb}"})
                    if d.get("status") == "success":
                        yield send({"type":"done"})
                        return
                except Exception:
                    pass
            yield send({"type":"done"})
        except Exception as e:
            yield send({"type":"error","msg":str(e)})
    
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


# ─── Setup: mark complete ───
@app.route("/setup/complete", methods=["POST"])
def setup_complete():
    # Create Desktop Shortcut
    try:
        import os
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        path = os.path.join(desktop, 'Jarvis AI.lnk')
        target = os.path.join(PROJECT_DIR, 'run_jarvis.bat')
        icon = os.path.join(PROJECT_DIR, 'static', 'logo.ico')
        
        vbs_script = f'''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target}"
oLink.WorkingDirectory = "{PROJECT_DIR}"
oLink.IconLocation = "{icon}"
oLink.Save()'''
        
        vbs_path = os.path.join(PROJECT_DIR, 'create_shortcut.vbs')
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_script)
        import subprocess
        subprocess.run(['cscript', '//nologo', vbs_path], creationflags=subprocess.CREATE_NO_WINDOW)
        os.remove(vbs_path)
    except Exception as e:
        print(f"Failed to create desktop shortcut: {e}")

    with open(SETUP_DONE_FILE, "w") as f:
        f.write("done")
    return jsonify({"ok": True})

@app.route("/shutdown", methods=["POST"])
def shutdown():
    import os, signal
    print("[SERVER] Shutdown requested. Bye!")
    os.kill(os.getpid(), signal.SIGTERM)
    return jsonify({"ok": True})


@app.route("/chat", methods=["POST"])
def chat():
    global active_conv, is_generating, _last_model_load_time
    is_generating = True
    _last_model_load_time = time.time()
    data = request.json
    message_text = data.get("message", "")
    images = data.get("images", [])
    model = data.get("model", "").strip()
    conv_id = data.get("conv_id")
    vision_mode = data.get("vision_mode", "vlm")
    stt_mode = data.get("stt_mode", "browser")
    tts_mode = data.get("tts_mode", "none")
    engine = data.get("engine", "local")

    os.environ["JARVIS_VISION_MODE"] = vision_mode

    # If no model specified and local engine, try to find first loaded model
    if not model and engine == "local":
        try:
            r = ollama_session.get(f"{OLLAMA_BASE}/api/ps", timeout=3)
            if r.status_code == 200:
                loaded = r.json().get("models", [])
                if loaded:
                    model = loaded[0].get("name", loaded[0].get("model", "gemma4:e4b"))
        except:
            pass
        if not model:
            model = "gemma4:e4b"  # Ultimate fallback
            
    if engine == "cloud" and not model:
        model = "claude-3-5-sonnet-20241022"

    print(f"\n[🤖 CHAT] Engine: {engine.upper()} | Model: {model} | Message: {message_text[:60]}")

    # Create conversation if none active
    if not conv_id:
        conv = create_conversation(message_text[:40] if message_text else "שיחה חדשה")
        conv_id = conv["id"]
    
    active_conv["id"] = conv_id
    
    # Load conversation history
    conv_data = get_conversation(conv_id)
    chat_history = conv_data["messages"] if conv_data else []

    message_obj = {"role": "user", "content": message_text or "Describe what you see/hear in the attached media."}
    if images:
        message_obj["images"] = [img.split(",")[1] if "," in img else img for img in images]

    chat_history.append(message_obj)

    # Auto-title on first message
    if len(chat_history) == 1 and message_text:
        auto_title(conv_id, message_text)

    # Trim history - keep last 4 messages for speed (less context = faster TTFT)
    if len(chat_history) > 4:
        chat_history = chat_history[-4:]
    
    # Strip images AND large tool results from old messages to reduce context size
    for i, m in enumerate(chat_history[:-1]):  # keep images/full content only on latest message
        if "images" in m:
            del m["images"]
        # Strip bloated [TOOL RESULT: ...] content from older messages
        if m.get("role") == "user" and m.get("content", "").startswith("[TOOL RESULT:"):
            # Keep only first 200 chars as a reminder, not the full dump
            m["content"] = m["content"][:200] + "... [נקצר מהיסטוריה]"

    # Reset abort flag
    abort_evt = threading.Event()
    active_generation["abort"] = abort_evt

    q = queue.Queue()
    
    # Import cloud engine if needed
    if engine == "cloud":
        from cloud_brain import run_cloud_chat_stream
    
    def run_model():
        nonlocal chat_history
        max_loops = 15
        loop = 0
        while loop < max_loops:
            if abort_evt.is_set():
                q.put({"type": "error", "content": "ההפקה הופסקה"})
                q.put(None)
                return
            loop += 1
            full_raw = ""
            cmds = []
            try:
                stream_gen = run_cloud_chat_stream(list(chat_history), model, vision_mode) if engine == "cloud" else run_gemma_chat_stream(list(chat_history), model, vision_mode)
                
                sentence_buf = ""
                in_think_block = False

                def _gen_tts(txt):
                    import tts_engine
                    audio_b64 = tts_engine.generate_speech_b64(txt, tts_mode)
                    if audio_b64:
                        q.put({"type": "tts_audio", "audio_b64": audio_b64})

                for chunk in stream_gen:
                    if abort_evt.is_set():
                        q.put({"type": "error", "content": "ההפקה הופסקה"})
                        q.put(None)
                        return
                    
                    if chunk.get("type") == "done":
                        if tts_mode != "none" and sentence_buf.strip():
                            threading.Thread(target=_gen_tts, args=(sentence_buf.strip(),), daemon=True).start()
                            sentence_buf = ""
                            
                        full_raw = chunk["raw"]
                        cmds = chunk["commands"]
                        if cmds:
                            chunk["type"] = "intermediate_done"
                        q.put(chunk)
                    else:
                        q.put(chunk)
                        
                        if chunk.get("type") == "content" and tts_mode != "none":
                            c_text = chunk.get("content", "")
                            
                            # Extremely simple tag heuristic to avoid reading <think>
                            if "<think>" in c_text: in_think_block = True
                            if "</think>" in c_text: in_think_block = False
                            
                            if not in_think_block and "<" not in c_text and ">" not in c_text:
                                sentence_buf += c_text
                                if any(x in c_text for x in [".", "!", "?", "\n", ":"]):
                                    txt_to_speak = sentence_buf.strip()
                                    sentence_buf = ""
                                    if txt_to_speak and len(txt_to_speak) > 2:
                                        threading.Thread(target=_gen_tts, args=(txt_to_speak,), daemon=True).start()
            except Exception as e:
                q.put({"type": "error", "content": str(e)})
                q.put(None)
                return

            # Strip <think> blocks
            import re
            memory_raw = re.sub(r'<think>.*?</think>', '', full_raw, flags=re.DOTALL | re.IGNORECASE).strip()
            chat_history.append({"role": "assistant", "content": memory_raw})

            if cmds:
                extracted_b64 = None
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                # Extract and stream narrations first to maintain UI order
                for cmd in cmds:
                    narration = cmd.pop("narration", None)
                    if narration:
                        q.put({"type": "narration", "content": narration})

                results_str_parts = []
                
                # Execute tools in parallel
                with ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_cmd = {executor.submit(execute_parsed_tool, cmd): cmd for cmd in cmds}
                    
                    for fut in as_completed(future_to_cmd):
                        cmd = future_to_cmd[fut]
                        try:
                            result = fut.result()
                        except Exception as e:
                            result = f"Tool error: {e}"
                            
                        # Handle screenshot vision injection
                        if cmd.get("tool") == "computer_action" and cmd.get("args", {}).get("action") == "screenshot":
                            try:
                                import json
                                res_json = json.loads(result)
                                if "image_b64" in res_json:
                                    extracted_b64 = res_json.pop("image_b64")
                                    result = json.dumps(res_json, ensure_ascii=False)
                                    q.put({"type": "agent_vision", "image": extracted_b64, "tool": "screenshot"})
                            except:
                                pass
                                
                        q.put({"type": "action_result", "tool": cmd.get("tool"), "result": str(result)})

                        # Trim individual tool result
                        res_str = str(result)
                        if len(res_str) > 2500:
                            res_str = res_str[:2500] + "\n... [נקצר - יש עוד תוצאות]"
                        
                        results_str_parts.append(f"[TOOL RESULT: {cmd.get('tool')}]\n{res_str}")

                # Combine all results
                combined_results = "\n\n".join(results_str_parts)
                if len(combined_results) > 6000:
                    combined_results = combined_results[:6000] + "\n... [נקצר - יש עוד תוצאות]"
                
                # For tools that return rich content, ask for detailed structured summary
                needs_rich_summary = any(c.get('tool') in ('read_telegram_news', 'search_web', 'deep_research', 'read_webpage', 'read_url') for c in cmds)
                
                if needs_rich_summary:
                    post_instruction = (
                        "---\n"
                        "סכם את המידע לעיל בעברית, בצורה מובנית:\n"
                        "- כתוב כותרות נושא + נקודות bullet (•)\n"
                        "- מיין לפי חשיבות\n"
                        "- ציין מקורות בסוגריים\n"
                        "- אל תפעיל כלים נוספים\n"
                        "- התעלם מפרסומות, זימונים לערוץ, ותוכן לא רלוונטי"
                    )
                else:
                    post_instruction = (
                        "---\n"
                        "עכשיו ענה למשתמש בעברית, קצר ולעניין (2-3 משפטים). "
                        "אל תפעיל כלים נוספים. תן את התשובה ישירות."
                    )
                
                tool_result_content = (
                    f"{combined_results}\n\n"
                    f"{post_instruction}"
                )
                tool_reply = {"role": "user", "content": tool_result_content}
                if extracted_b64:
                    tool_reply["images"] = [extracted_b64]
                    
                chat_history.append(tool_reply)
                q.put({"type": "re_think"})
            else:
                break
        
        # Save to DB (strip images for storage)
        save_history = []
        for m in chat_history:
            sm = {"role": m["role"], "content": m["content"]}
            save_history.append(sm)
        save_messages(conv_id, save_history)
        
        global is_generating
        is_generating = False
        q.put(None)

    t = threading.Thread(target=run_model, daemon=True)
    active_generation["thread"] = t
    t.start()

    def generate():
        try:
            # Send conv_id to client
            yield f"data: {json.dumps({'type': 'conv_id', 'id': conv_id})}\n\n"
            while True:
                try:
                    chunk = q.get(timeout=2)
                    if chunk is None:
                        break
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    if abort_evt.is_set():
                        break
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
            yield "event: close\ndata: \n\n"
        finally:
            global is_generating
            is_generating = False

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/api/logs", methods=["GET"])
def api_logs():
    return jsonify({"logs": "".join(log_buffer.q)})

@app.route("/api/logs/stream")
def stream_logs():
    def generate():
        last_logs = ""
        while True:
            current_logs = "".join(log_buffer.q)
            if current_logs != last_logs:
                yield f"data: {json.dumps({'logs': current_logs})}\n\n"
                last_logs = current_logs
            time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
