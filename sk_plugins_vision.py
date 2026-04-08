# sk_plugins_vision.py
# =====================
# Vision Plugin - Screen Reading with OCR
# Requires: pip install pytesseract pillow pyautogui
# Also requires: Tesseract OCR installed on system

import os
import shutil
from typing import Annotated
from semantic_kernel.functions import kernel_function


def check_tesseract_installed():
    """Check if Tesseract OCR is available on the system."""
    # Check common Windows paths
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        shutil.which("tesseract"),  # Check PATH
    ]
    
    for path in tesseract_paths:
        if path and os.path.exists(path):
            return path
    
    return None


class VisionPlugin:
    """
    Screen reading using OCR.
    Captures screen and extracts text using Tesseract.
    """
    
    def __init__(self):
        self.tesseract_path = check_tesseract_installed()
        if self.tesseract_path:
            print("[VISION] Tesseract found at:", self.tesseract_path)
        else:
            print("[VISION] WARNING: Tesseract OCR not installed!")
            print("[VISION] Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    
    @kernel_function(
        name="read_screen",
        description="Read text from the screen using OCR. Use when user says 'read screen', 'what's on screen', 'look at screen'"
    )
    def read_screen(self) -> str:
        """Capture screen and extract text using OCR."""
        
        # Check Tesseract first
        if not self.tesseract_path:
            return "Error: Tesseract OCR is not installed on this PC. Please install from: https://github.com/UB-Mannheim/tesseract/wiki"
        
        try:
            import pyautogui
            from PIL import Image
            import pytesseract
            import time
            
            # Set tesseract path
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            # Give user time to switch windows
            print("[VISION] Scanning in 4 seconds... SWITCH WINDOW NOW!")
            time.sleep(4)
            
            # Capture screen
            screenshot = pyautogui.screenshot()
            
            # Extract text (English + Hebrew)
            text = pytesseract.image_to_string(screenshot, lang='eng+heb')
            
            # Clean up text
            text = text.strip()
            
            if not text:
                return "Screen captured but no readable text found."
            
            # Truncate if too long
            if len(text) > 1000:
                text = text[:1000] + "... (truncated)"
            
            return "Screen text:\n" + text
            
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else "unknown"
            return "Error: Missing library '{}'. Run: pip install pytesseract pillow pyautogui".format(missing)
        except Exception as e:
            return "Error reading screen: " + str(e)
    
    @kernel_function(
        name="read_area",
        description="Read text from a specific area of the screen"
    )
    def read_area(
        self,
        x: Annotated[int, "X coordinate (left)"] = 0,
        y: Annotated[int, "Y coordinate (top)"] = 0,
        width: Annotated[int, "Width of area"] = 800,
        height: Annotated[int, "Height of area"] = 600
    ) -> str:
        """Capture a specific area and extract text."""
        
        if not self.tesseract_path:
            return "Error: Tesseract OCR is not installed. Install from: https://github.com/UB-Mannheim/tesseract/wiki"
        
        try:
            import pyautogui
            from PIL import Image
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            # Capture specific region
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            # Extract text (English + Hebrew)
            text = pytesseract.image_to_string(screenshot, lang='eng+heb').strip()
            
            if not text:
                return "No readable text in the specified area."
            
            if len(text) > 500:
                text = text[:500] + "..."
            
            return "Area text:\n" + text
            
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="take_screenshot",
        description="Take a screenshot and save it"
    )
    def take_screenshot_and_save(self) -> str:
        """Take a screenshot and save to desktop."""
        try:
            import pyautogui
            from datetime import datetime
            
            # Save path
            desktop = os.path.expanduser("~/Desktop")
            filename = "screenshot_{}.png".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
            filepath = os.path.join(desktop, filename)
            
            # Capture and save
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            return "Screenshot saved to: " + filepath
            
        except Exception as e:
            return "Error: " + str(e)


# Export
VISION_PLUGINS = [
    VisionPlugin,
]
