"""
Jarvis.pyw
Ultra-fast launcher: shows splash screen in <1s, loads server in background.
Handles zombie processes from previous runs.
"""
import os
import sys
import time
import threading
import socket
import subprocess
import requests

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_DIR)

PORT = 5000
URL = f"http://127.0.0.1:{PORT}"
TITLE = "Jarvis — AI Personal Assistant"
LOGO_ICO = os.path.join(PROJECT_DIR, "static", "logo.ico")
LOGO_PNG = os.path.join(PROJECT_DIR, "static", "logo.png")

SPLASH_HTML = r"""
<!DOCTYPE html>
<html dir="rtl" lang="he"><head><meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400&display=swap');
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    background: #080810;
    display: flex; align-items: center; justify-content: center;
    height: 100vh; font-family: 'Heebo', 'Segoe UI', sans-serif;
    overflow: hidden;
  }
  .splash { text-align: center; color: #e2e8f0; animation: fadeIn 0.4s ease-out; }
  .logo {
    font-size: 3.2em; letter-spacing: 10px; font-weight: 300;
    background: linear-gradient(135deg, #00e5ff, #7c3aed);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 16px; direction: ltr;
  }
  .sub { color: #94a3b8; font-size: 0.95em; margin-bottom: 24px; direction: ltr; }
  .dots { display: flex; gap: 8px; justify-content: center; margin-bottom: 20px; }
  .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #00e5ff; opacity: 0.3;
    animation: pulse 1.2s ease-in-out infinite;
  }
  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }
  .status {
    font-size: 0.85em; color: #64748b;
    font-family: 'Heebo', sans-serif;
    direction: rtl; min-height: 1.5em;
  }
  @keyframes fadeIn { from{opacity:0;transform:scale(0.95)}to{opacity:1;transform:scale(1)} }
  @keyframes pulse { 0%,100%{opacity:0.2;transform:scale(0.8)}50%{opacity:1;transform:scale(1.2)} }
</style>
</head><body>
<div class="splash">
  <div class="logo">JARVIS</div>
  <div class="sub">AI Personal Assistant</div>
  <div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
  <div class="status" id="st">טוען מערכת...</div>
</div>
<script>
  function setStatus(msg) { document.getElementById('st').textContent = msg; }
</script>
</body></html>
"""


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def is_server_alive():
    """Check if there's a HEALTHY server on the port (not a zombie)."""
    try:
        r = requests.get(URL, timeout=2)
        return r.status_code < 500
    except:
        return False


def kill_zombie_on_port(port):
    """Kill any process holding the port (zombie from previous crash)."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"(Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue).OwningProcess | "
             f"ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"],
            capture_output=True, text=True, timeout=5
        )
    except:
        pass
    # Wait a bit for the port to free up
    time.sleep(0.5)


def run_server():
    """Import and start Flask in background thread."""
    # If port is in use, check if it's alive
    if is_port_in_use(PORT):
        if is_server_alive():
            return  # Server already running and healthy, skip
        else:
            # Zombie process — kill it
            kill_zombie_on_port(PORT)

    from app import app
    app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True)


def wait_and_redirect(window):
    """Wait for server to be ready, then navigate the window to the real app."""

    def set_status(msg):
        try:
            window.evaluate_js(f'setStatus("{msg}")')
        except:
            pass

    time.sleep(0.3)
    set_status("טוען שרת...")

    status_msgs = [
        (1.5, "מחבר מנוע AI..."),
        (3, "טוען כלים ומודולים..."),
        (5, "מאתחל Ollama..."),
        (8, "מכין ממשק משתמש..."),
        (12, "כמעט מוכן..."),
        (20, "השרת לוקח קצת זמן..."),
    ]
    msg_idx = 0
    start = time.time()

    while time.time() - start < 40:
        elapsed = time.time() - start

        while msg_idx < len(status_msgs) and elapsed >= status_msgs[msg_idx][0]:
            set_status(status_msgs[msg_idx][1])
            msg_idx += 1

        try:
            r = requests.get(URL, timeout=1.5)
            if r.status_code < 500:
                set_status("מוכן! פותח ג׳ארוויס...")
                time.sleep(0.4)
                window.load_url(URL)
                return
        except:
            pass
        time.sleep(0.4)

    set_status("שגיאה: השרת לא עלה. נסה להריץ python app.py בנפרד.")


if __name__ == "__main__":
    # 1. Start server in background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # 2. Open window IMMEDIATELY with splash
    try:
        import webview
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('elchanan.jarvis.assistant')

        icon_path = LOGO_ICO if os.path.exists(LOGO_ICO) else (LOGO_PNG if os.path.exists(LOGO_PNG) else None)

        window = webview.create_window(
            title=TITLE,
            html=SPLASH_HTML,
            width=1200,
            height=820,
            min_size=(800, 600),
            background_color="#080810",
            easy_drag=False,
        )

        webview.start(
            func=wait_and_redirect,
            args=[window],
            gui='edgechromium',
            debug=False,
            private_mode=False,
        )
        os._exit(0)

    except Exception as e:
        print(f"pywebview error: {e}, falling back to browser...")
        start = time.time()
        while time.time() - start < 25:
            try:
                r = requests.get(URL, timeout=1)
                if r.status_code < 500:
                    break
            except:
                time.sleep(0.5)
        import webbrowser
        webbrowser.open(URL)
        while True:
            time.sleep(1)
