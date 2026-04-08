try:
    import semantic_kernel
    print("semantic_kernel: OK")
except ImportError:
    print("semantic_kernel: MISSING")

try:
    import screen_brightness_control
    print("screen_brightness_control: OK")
except ImportError:
    print("screen_brightness_control: MISSING")

try:
    import pyautogui
    print("pyautogui: OK")
except ImportError:
    print("pyautogui: MISSING")

try:
    import speedtest
    print("speedtest: OK")
except ImportError:
    print("speedtest: MISSING")

try:
    import duckduckgo_search
    print("duckduckgo_search: OK")
except ImportError:
    print("duckduckgo_search: MISSING")

try:
    import pywhatkit
    print("pywhatkit: OK")
except ImportError:
    print("pywhatkit: MISSING")
