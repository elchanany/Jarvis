"""
Jarvis Native Window Launcher
Opens the Jarvis web app as a native desktop window using pywebview.
Falls back to Chrome App Mode if pywebview is unavailable.
"""
import time
import subprocess
import sys
import os
import requests

PORT = 5000
URL = f"http://127.0.0.1:{PORT}"
TITLE = "Jarvis — AI Personal Assistant"
LOGO = os.path.join(os.path.dirname(__file__), "static", "logo.png")

def wait_for_server(timeout=15):
    """Wait until Flask is ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(URL, timeout=1)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def open_native_window():
    """Try pywebview first, then fallback to Chrome app mode."""
    try:
        import webview
        
        # Window settings
        window = webview.create_window(
            title=TITLE,
            url=URL,
            width=1200,
            height=820,
            min_size=(800, 600),
            background_color="#080c10",
            easy_drag=False,
        )
        
        # Set logo if available
        # Note: icon can be set on the webview.start call
        icon = LOGO if os.path.exists(LOGO) else None
        
        webview.start(
            debug=False,
            private_mode=False,
            icon=icon,
        )
        return True
    except ImportError:
        return False

def open_chrome_app_mode():
    """Fallback: open in Chrome/Edge as a borderless app window."""
    # Try Chrome first, then Edge
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            subprocess.run([
                path,
                f"--app={URL}",
                "--window-size=1200,820",
                "--disable-extensions",
                "--no-first-run",
            ])
            return True
    
    # Last resort: open in default browser
    import webbrowser
    webbrowser.open(URL)
    # Keep alive
    print("Jarvis is running in your browser at", URL)
    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    return True

def main():
    print("Waiting for Jarvis server...")
    if not wait_for_server():
        print("ERROR: Server did not start in time!")
        sys.exit(1)
    
    print("Server ready! Opening window...")
    
    # Try native window first
    if not open_native_window():
        print("pywebview not available, using Chrome app mode...")
        open_chrome_app_mode()

if __name__ == "__main__":
    main()
