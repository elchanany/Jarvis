# sk_plugins.py
# ==============
# Semantic Kernel Plugins for Jarvis
# Native Windows interaction using @kernel_function decorators

import os
import subprocess
from typing import Annotated
from semantic_kernel.functions import kernel_function


# ============================================
# Windows Plugin - App Launching & System Control
# ============================================

class WindowsPlugin:
    """Plugin for Windows OS interaction - app launching, volume, media control."""
    
    # App paths mapping
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
    }
    
    @kernel_function(
        name="launch_app",
        description="Launch an application on Windows. Use for: open chrome, start spotify, launch notepad"
    )
    def launch_app(
        self,
        app_name: Annotated[str, "Name of the app to launch (chrome, spotify, notepad, etc.)"]
    ) -> str:
        """Launch a Windows application."""
        app_lower = app_name.lower().strip()
        
        # Check known apps
        if app_lower in self.APP_PATHS:
            try:
                subprocess.Popen("start " + self.APP_PATHS[app_lower], shell=True)
                return "Launched " + app_name
            except Exception as e:
                return "Error: " + str(e)
        
        # Check websites
        if app_lower in self.WEBSITES:
            try:
                subprocess.Popen("start " + self.WEBSITES[app_lower], shell=True)
                return "Opened " + app_name
            except Exception as e:
                return "Error: " + str(e)
        
        # Try direct launch
        try:
            subprocess.Popen("start " + app_name, shell=True)
            return "Attempting to launch " + app_name
        except:
            return "Could not find: " + app_name
    
    @kernel_function(
        name="open_url",
        description="Open a URL in the default browser"
    )
    def open_url(
        self,
        url: Annotated[str, "The URL to open"]
    ) -> str:
        """Open a URL in browser."""
        try:
            if not url.startswith("http"):
                url = "https://" + url
            subprocess.Popen("start " + url, shell=True)
            return "Opened " + url
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="set_volume",
        description="Control system volume: up, down, mute, unmute"
    )
    def set_volume(
        self,
        action: Annotated[str, "Volume action: up, down, mute, or unmute"]
    ) -> str:
        """Control Windows volume."""
        try:
            import pyautogui
            
            action_lower = action.lower().strip()
            
            if action_lower in ["up", "increase", "louder"]:
                pyautogui.press("volumeup")
                pyautogui.press("volumeup")
                return "Volume increased"
            elif action_lower in ["down", "decrease", "lower", "quieter"]:
                pyautogui.press("volumedown")
                pyautogui.press("volumedown")
                return "Volume decreased"
            elif action_lower in ["mute", "silent"]:
                pyautogui.press("volumemute")
                return "System volume muted"
            elif action_lower == "unmute":
                pyautogui.press("volumemute")
                return "Unmuted"
            else:
                return "Unknown action: " + action
        except ImportError:
            return "pyautogui not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="control_media",
        description="Control media playback: play, pause, next, previous, stop"
    )
    def control_media(
        self,
        action: Annotated[str, "Media action: play, pause, next, previous, stop"]
    ) -> str:
        """Control media playback."""
        try:
            import pyautogui
            
            action_lower = action.lower().strip()
            
            if action_lower in ["play", "pause", "playpause"]:
                pyautogui.press("playpause")
                return "Toggled play/pause"
            elif action_lower in ["next", "skip"]:
                pyautogui.press("nexttrack")
                return "Next track"
            elif action_lower in ["previous", "prev", "back"]:
                pyautogui.press("prevtrack")
                return "Previous track"
            elif action_lower == "stop":
                pyautogui.press("stop")
                return "Stopped"
            else:
                return "Unknown action: " + action
        except ImportError:
            return "pyautogui not installed"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="lock_screen",
        description="Lock the Windows screen"
    )
    def lock_screen(self) -> str:
        """Lock the workstation."""
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Screen locked"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="take_screenshot",
        description="Take a screenshot using the snipping tool"
    )
    def take_screenshot(self) -> str:
        """Open screenshot tool."""
        try:
            subprocess.Popen("snippingtool", shell=True)
            return "Screenshot tool opened"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="play_on_youtube",
        description="Play a song or video on YouTube. ONLY use when user says 'play song' or 'watch video'"
    )
    def play_on_youtube(
        self,
        query: Annotated[str, "The song or video name to play on YouTube"]
    ) -> str:
        """Play something on YouTube using pywhatkit (auto-plays first result)."""
        try:
            import pywhatkit
            
            # pywhatkit.playonyt finds first video and opens direct URL
            pywhatkit.playonyt(query)
            return "Playing '" + query + "' on YouTube"
        except ImportError:
            # Fallback to browser if pywhatkit not installed
            import webbrowser
            import urllib.parse
            safe_query = urllib.parse.quote_plus(query)
            url = "https://www.youtube.com/results?search_query=" + safe_query
            webbrowser.open(url)
            return "Opening YouTube for '" + query + "'. (Install pywhatkit for auto-play)"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="ask_confirmation",
        description="Ask the user for confirmation (yes/no) before proceeding with a dangerous action."
    )
    def ask_confirmation(self, question: str) -> str:
        """Ask user for confirmation."""
        # This returns the question string, which Jarvis will speak/print.
        # The next user input will be handled by jarvis_layers PENDING_ACTION logic.
        return "CONFIRM: " + question


# ============================================
# FileIO Plugin - File Operations
# ============================================

class FileIOPlugin:
    """Plugin for file system operations."""
    
    @kernel_function(
        name="list_files",
        description="List files in a directory (documents, desktop, downloads)"
    )
    def list_files(
        self,
        directory: Annotated[str, "Directory: documents, desktop, downloads, or full path"]
    ) -> str:
        """List files in a directory."""
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
            files = os.listdir(path)[:20]
            if not files:
                return "Directory is empty"
            
            result = "Files in " + directory + ":\n"
            for f in files:
                full = os.path.join(path, f)
                prefix = "[DIR] " if os.path.isdir(full) else "      "
                result += prefix + f + "\n"
            return result
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="search_file",
        description="Search for a file by name in common directories"
    )
    def search_file(
        self,
        filename: Annotated[str, "Name or part of filename to search"]
    ) -> str:
        """Search for files."""
        search_dirs = [
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
        ]
        
        found = []
        filename_lower = filename.lower()
        
        for base in search_dirs:
            if not os.path.exists(base):
                continue
            try:
                for root, dirs, files in os.walk(base):
                    for f in files:
                        if filename_lower in f.lower():
                            found.append(os.path.join(root, f))
                            if len(found) >= 10:
                                break
                    if len(found) >= 10:
                        break
            except:
                pass
        
        if not found:
            return "No files found matching: " + filename
        
        result = "Found " + str(len(found)) + " file(s):\n"
        for f in found:
            result += "  - " + f + "\n"
        return result
    
    @kernel_function(
        name="read_file",
        description="Read the contents of a text file"
    )
    def read_file(
        self,
        filepath: Annotated[str, "Path to the file to read"]
    ) -> str:
        """Read a file."""
        try:
            # Expand user path
            filepath = os.path.expanduser(filepath)
            
            if not os.path.exists(filepath):
                return "File not found: " + filepath
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read(5000)  # Limit to 5KB
            
            if len(content) == 5000:
                content += "\n... (truncated)"
            
            return content
        except Exception as e:
            return "Error reading file: " + str(e)
    
    @kernel_function(
        name="write_file",
        description="Write content to a file"
    )
    def write_file(
        self,
        filepath: Annotated[str, "Path to the file to write"],
        content: Annotated[str, "Content to write to the file"]
    ) -> str:
        """Write to a file."""
        try:
            filepath = os.path.expanduser(filepath)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            
            return "Written to " + filepath
        except Exception as e:
            return "Error writing file: " + str(e)
    
    @kernel_function(
        name="delete_file",
        description="Delete a file. DANGEROUS - requires confirmation!"
    )
    def delete_file(
        self,
        filepath: Annotated[str, "Path to the file to delete"]
    ) -> str:
        """Delete a file."""
        try:
            filepath = os.path.expanduser(filepath)
            
            if not os.path.exists(filepath):
                return "File not found: " + filepath
            
            os.remove(filepath)
            return "Deleted: " + filepath
        except Exception as e:
            return "Error deleting file: " + str(e)
    
    @kernel_function(
        name="move_file",
        description="Move a file from one location to another"
    )
    def move_file(
        self,
        source: Annotated[str, "Source file path"],
        destination: Annotated[str, "Destination path"]
    ) -> str:
        """Move a file."""
        try:
            import shutil
            source = os.path.expanduser(source)
            destination = os.path.expanduser(destination)
            
            if not os.path.exists(source):
                return "Source not found: " + source
            
            shutil.move(source, destination)
            return f"Moved {source} to {destination}"
        except Exception as e:
            return "Error moving file: " + str(e)
    
    @kernel_function(
        name="copy_file",
        description="Copy a file to another location"
    )
    def copy_file(
        self,
        source: Annotated[str, "Source file path"],
        destination: Annotated[str, "Destination path"]
    ) -> str:
        """Copy a file."""
        try:
            import shutil
            source = os.path.expanduser(source)
            destination = os.path.expanduser(destination)
            
            if not os.path.exists(source):
                return "Source not found: " + source
            
            shutil.copy2(source, destination)
            return f"Copied {source} to {destination}"
        except Exception as e:
            return "Error copying file: " + str(e)
    
    @kernel_function(
        name="rename_file",
        description="Rename a file or folder"
    )
    def rename_file(
        self,
        filepath: Annotated[str, "Current file path"],
        new_name: Annotated[str, "New name for the file"]
    ) -> str:
        """Rename a file."""
        try:
            filepath = os.path.expanduser(filepath)
            
            if not os.path.exists(filepath):
                return "File not found: " + filepath
            
            directory = os.path.dirname(filepath)
            new_path = os.path.join(directory, new_name)
            os.rename(filepath, new_path)
            return f"Renamed to {new_name}"
        except Exception as e:
            return "Error renaming: " + str(e)
    
    @kernel_function(
        name="create_folder",
        description="Create a new folder/directory"
    )
    def create_folder(
        self,
        path: Annotated[str, "Path for the new folder"]
    ) -> str:
        """Create a folder."""
        try:
            path = os.path.expanduser(path)
            os.makedirs(path, exist_ok=True)
            return "Created folder: " + path
        except Exception as e:
            return "Error creating folder: " + str(e)
    
    @kernel_function(
        name="delete_folder",
        description="Delete a folder and all its contents. DANGEROUS!"
    )
    def delete_folder(
        self,
        path: Annotated[str, "Path to the folder to delete"]
    ) -> str:
        """Delete a folder."""
        try:
            import shutil
            path = os.path.expanduser(path)
            
            if not os.path.exists(path):
                return "Folder not found: " + path
            
            shutil.rmtree(path)
            return "Deleted folder: " + path
        except Exception as e:
            return "Error deleting folder: " + str(e)
    
    @kernel_function(
        name="open_file",
        description="Open a file with its default application"
    )
    def open_file(
        self,
        filepath: Annotated[str, "Path to the file to open"]
    ) -> str:
        """Open a file with default app."""
        try:
            filepath = os.path.expanduser(filepath)
            
            if not os.path.exists(filepath):
                return "File not found: " + filepath
            
            os.startfile(filepath)
            return "Opened: " + filepath
        except Exception as e:
            return "Error opening file: " + str(e)
    
    @kernel_function(
        name="get_file_info",
        description="Get information about a file (size, date, type)"
    )
    def get_file_info(
        self,
        filepath: Annotated[str, "Path to the file"]
    ) -> str:
        """Get file information."""
        try:
            from datetime import datetime
            filepath = os.path.expanduser(filepath)
            
            if not os.path.exists(filepath):
                return "File not found: " + filepath
            
            stat = os.stat(filepath)
            size_bytes = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            
            # Human readable size
            if size_bytes < 1024:
                size_str = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024*1024):.1f} MB"
            
            is_dir = "Folder" if os.path.isdir(filepath) else "File"
            ext = os.path.splitext(filepath)[1] or "No extension"
            
            return f"{is_dir}: {os.path.basename(filepath)}\nSize: {size_str}\nType: {ext}\nModified: {modified}"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="sort_files",
        description="Sort files in a folder by type into subfolders"
    )
    def sort_files_by_type(
        self,
        folder: Annotated[str, "Folder to organize"]
    ) -> str:
        """Sort files by type into subfolders."""
        try:
            import shutil
            folder = os.path.expanduser(folder)
            
            if not os.path.isdir(folder):
                return "Not a folder: " + folder
            
            type_map = {
                ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
                ".mp3": "Music", ".wav": "Music", ".flac": "Music",
                ".mp4": "Videos", ".avi": "Videos", ".mkv": "Videos", ".mov": "Videos",
                ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents", ".txt": "Documents",
                ".zip": "Archives", ".rar": "Archives", ".7z": "Archives",
                ".exe": "Programs", ".msi": "Programs",
            }
            
            moved = 0
            for file in os.listdir(folder):
                filepath = os.path.join(folder, file)
                if os.path.isfile(filepath):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in type_map:
                        dest_folder = os.path.join(folder, type_map[ext])
                        os.makedirs(dest_folder, exist_ok=True)
                        shutil.move(filepath, dest_folder)
                        moved += 1
            
            return f"Organized {moved} files into subfolders"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="empty_recycle_bin",
        description="Empty the Windows Recycle Bin. DANGEROUS!"
    )
    def empty_recycle_bin(self) -> str:
        """Empty recycle bin."""
        try:
            import ctypes
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
            return "Recycle bin emptied"
        except Exception as e:
            return "Error: " + str(e)


# ============================================
# Time Plugin - Time & Date (Human Readable)
# ============================================

class TimePlugin:
    """Plugin for time-related functions."""
    
    @kernel_function(
        name="get_time",
        description="Get the current time"
    )
    def get_time(self) -> str:
        """Get current time - EXACT time only."""
        from datetime import datetime
        now = datetime.now()
        # Return exact time in 24h format like "09:05"
        return now.strftime('%H:%M')
    
    @kernel_function(
        name="get_date",
        description="Get the current date"
    )
    def get_date(self) -> str:
        """Get current date."""
        from datetime import datetime
        return "Today is " + datetime.now().strftime("%A, %B %d, %Y")
    
    @kernel_function(
        name="get_day",
        description="Get the current day of the week"
    )
    def get_day(self) -> str:
        """Get current day."""
        from datetime import datetime
        return "Today is " + datetime.now().strftime("%A")
    
    @kernel_function(
        name="get_datetime",
        description="Get both current date and time"
    )
    def get_datetime(self) -> str:
        """Get current date and time."""
        from datetime import datetime
        now = datetime.now()
        return "It is " + now.strftime("%I:%M %p on %A, %B %d, %Y")


# ============================================
# Power Control Plugin - Shutdown/Restart/Sleep
# ============================================

class PowerPlugin:
    """Plugin for system power control - shutdown, restart, sleep."""
    
    @kernel_function(
        name="shutdown_pc",
        description="Shutdown the computer. DANGEROUS - use with caution!"
    )
    def shutdown_pc(self) -> str:
        """Shutdown the computer."""
        try:
            subprocess.run(["shutdown", "/s", "/t", "60"], check=True)
            return "Computer will shut down in 60 seconds. To cancel: shutdown /a"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="cancel_shutdown",
        description="Cancel a scheduled shutdown"
    )
    def cancel_shutdown(self) -> str:
        """Cancel shutdown."""
        try:
            subprocess.run(["shutdown", "/a"], check=True)
            return "Shutdown cancelled"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="restart_pc",
        description="Restart the computer. DANGEROUS - use with caution!"
    )
    def restart_pc(self) -> str:
        """Restart the computer."""
        try:
            subprocess.run(["shutdown", "/r", "/t", "60"], check=True)
            return "Computer will restart in 60 seconds. To cancel: shutdown /a"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="sleep_pc",
        description="Put the computer to sleep"
    )
    def sleep_pc(self) -> str:
        """Put computer to sleep."""
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
            return "Putting computer to sleep..."
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="logout",
        description="Log out of Windows"
    )
    def logout(self) -> str:
        """Log out."""
        try:
            subprocess.run(["shutdown", "/l"])
            return "Logging out..."
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="set_brightness",
        description="Set screen brightness (0-100)"
    )
    def set_brightness(
        self,
        level: Annotated[str, "Brightness level 0-100 or '+10', '-10'"]
    ) -> str:
        """Set screen brightness."""
        try:
            import screen_brightness_control as sbc
            
            # Handle incremental change
            target_level = level
            if isinstance(level, str):
                if '+' in level or '-' in level:
                    current = sbc.get_brightness()
                    current_val = current[0] if isinstance(current, list) else current
                    change = int(level)
                    target_level = max(0, min(100, current_val + change))
                else:
                    target_level = int(level)
            
            sbc.set_brightness(target_level)
            sbc.set_brightness(target_level)
            return f"Brightness set to {target_level}% (Delta: {level})"
        except ImportError:
            return "Install: pip install screen-brightness-control"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="get_brightness",
        description="Get current screen brightness"
    )
    def get_brightness(self) -> str:
        """Get screen brightness."""
        try:
            import screen_brightness_control as sbc
            level = sbc.get_brightness()
            return f"Current brightness: {level[0] if isinstance(level, list) else level}%"
        except ImportError:
            return "Install: pip install screen-brightness-control"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="get_battery",
        description="Get current battery percentage and status"
    )
    def get_battery(self) -> str:
        """Get battery status - returns percentage and charging status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery is None:
                return "No battery detected (desktop PC?)"
            percent = battery.percent
            charging = "charging" if battery.power_plugged else "on battery"
            return f"Battery: {percent}% ({charging})"
        except ImportError:
            return "Install: pip install psutil"
        except Exception as e:
            return "Error: " + str(e)


# ============================================
# Network Plugin - WiFi, IP, Speed
# ============================================

class NetworkPlugin:
    """Plugin for network information and control."""
    
    @kernel_function(
        name="get_ip_address",
        description="Get the computer's IP address"
    )
    def get_ip_address(self) -> str:
        """Get IP addresses."""
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            # Try to get public IP
            try:
                import urllib.request
                public_ip = urllib.request.urlopen('https://api.ipify.org', timeout=3).read().decode()
            except:
                public_ip = "Could not get public IP"
            
            return f"Computer: {hostname}\nLocal IP: {local_ip}\nPublic IP: {public_ip}"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="get_wifi_networks",
        description="List available WiFi networks"
    )
    def get_wifi_networks(self) -> str:
        """List WiFi networks."""
        try:
            # Fix encoding crash using errors='ignore'
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks"],
                capture_output=True
            )
            # Decode manually to handle Hebrew/special chars
            stdout = result.stdout.decode('cp862', errors='ignore') # Try Hebrew DOS encoding first
            
            networks = []
            for line in stdout.split('\n'):
                if 'SSID' in line and 'BSSID' not in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        ssid = parts[1].strip()
                        if ssid:
                            networks.append(ssid)
            
            if networks:
                return "Available networks:\n- " + "\n- ".join(networks[:10])
            return "No WiFi networks found"
        except Exception as e:
            # Fallback to simple ascii decode
            return "Error scanning networks: " + str(e)
    
        except Exception as e:
            return "Error: " + str(e)

    @kernel_function(
        name="check_internet_speed",
        description="Check internet connection speed (Download/Upload)"
    )
    def check_internet_speed(self) -> str:
        """Check internet speed using speedtest-cli."""
        try:
            import speedtest
            st = speedtest.Speedtest()
            st.get_best_server()
            down = st.download() / 1_000_000 # Mbps
            up = st.upload() / 1_000_000 # Mbps
            return f"Download: {down:.1f} Mbps\nUpload: {up:.1f} Mbps\nPing: {st.results.ping} ms"
        except ImportError:
            return "Install: pip install speedtest-cli"
        except Exception as e:
            return "Error testing speed: " + str(e)

    @kernel_function(
        name="toggle_wifi",
        description="Turn WiFi on or off"
    )
    def toggle_wifi(self, state: Annotated[str, "on or off"]) -> str:
        """Toggle WiFi using Windows Radio API (no admin required)."""
        import threading
        result_holder = {"result": None, "error": None}
        
        def run_in_thread():
            import asyncio
            try:
                from winsdk.windows.devices.radios import Radio, RadioState, RadioKind
                
                async def set_wifi_state(turn_on: bool):
                    radios = await Radio.get_radios_async()
                    for radio in radios:
                        if radio.kind == RadioKind.WI_FI:
                            target_state = RadioState.ON if turn_on else RadioState.OFF
                            await radio.set_state_async(target_state)
                            return True
                    return False
                
                turn_on = state.lower() == "on"
                # Create a NEW event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result_holder["result"] = loop.run_until_complete(set_wifi_state(turn_on))
                finally:
                    loop.close()
            except Exception as e:
                result_holder["error"] = str(e)
        
        # Run in a separate thread to avoid event loop conflicts
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=10)
        
        if result_holder["error"]:
            # Fallback to netsh
            try:
                cmd = "enable" if state.lower() == "on" else "disable"
                subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", f"admin={cmd}"], check=True)
                return f"WiFi turned {state} (via netsh)"
            except:
                return f"Failed to turn {state} WiFi: {result_holder['error']}"
        elif result_holder["result"]:
            return f"WiFi turned {state}"
        else:
            return "WiFi radio not found"

    @kernel_function(
        name="toggle_bluetooth",
        description="Turn Bluetooth on or off"
    )
    def toggle_bluetooth(self, state: Annotated[str, "on or off"]) -> str:
        """Toggle Bluetooth using Windows Radio API (no admin required)."""
        import threading
        result_holder = {"result": None, "error": None}
        
        def run_in_thread():
            import asyncio
            try:
                from winsdk.windows.devices.radios import Radio, RadioState, RadioKind
                
                async def set_bluetooth_state(turn_on: bool):
                    radios = await Radio.get_radios_async()
                    for radio in radios:
                        if radio.kind == RadioKind.BLUETOOTH:
                            target_state = RadioState.ON if turn_on else RadioState.OFF
                            await radio.set_state_async(target_state)
                            return True
                    return False
                
                turn_on = state.lower() == "on"
                # Create a NEW event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result_holder["result"] = loop.run_until_complete(set_bluetooth_state(turn_on))
                finally:
                    loop.close()
            except Exception as e:
                result_holder["error"] = str(e)
        
        # Run in a separate thread to avoid event loop conflicts
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join(timeout=10)  # Wait max 10 seconds
        
        if result_holder["error"]:
            # Fallback to Settings
            subprocess.run("start ms-settings:bluetooth", shell=True)
            action = "enable" if state == "on" else "disable"
            return f"Opening Bluetooth settings to {action}. (Error: {result_holder['error']})"
        elif result_holder["result"]:
            return f"Bluetooth turned {state}"
        else:
            return "Bluetooth radio not found"

    @kernel_function(
        name="connect_device",
        description="Connect to a specific device (headlines, speaker, phone)"
    )
    def connect_device(self, device_type: Annotated[str, "headphones, speaker, phone"]) -> str:
        """Connect to a known device."""
        import json
        
        # Load known devices
        devices_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "known_devices.json")
        try:
            with open(devices_file, "r") as f:
                known = json.load(f)
        except:
            known = {}

        device_name = known.get(device_type, device_type) # Use mapping or raw type
        
        # Open Bluetooth settings and tell user
        subprocess.run("start ms-settings:bluetooth", shell=True)
        return f"Opening Bluetooth settings for '{device_name}'. Please select it manually if not auto-connected."


# ============================================
# Memory Plugin - Remember Facts
# ============================================

class MemoryPlugin:
    """Plugin for remembering user information."""
    
    MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memories.json")
    
    @kernel_function(
        name="remember_fact",
        description="Remember a fact about the user"
    )
    def remember_fact(
        self,
        fact: Annotated[str, "The fact to remember"]
    ) -> str:
        """Save a fact to memory."""
        import json
        from datetime import datetime
        
        memories = []
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                    memories = json.load(f)
            except:
                memories = []
        
        memories.append({
            "fact": fact,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        
        with open(self.MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        
        return "I'll remember: " + fact
    
    @kernel_function(
        name="recall_memories",
        description="Recall what you remember about the user"
    )
    def recall_memories(self) -> str:
        """Recall saved memories."""
        import json
        
        if not os.path.exists(self.MEMORY_FILE):
            return "I don't have any memories saved yet."
        
        try:
            with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                memories = json.load(f)
            
            if not memories:
                return "I don't have any memories saved yet."
            
            result = "I remember:\n"
            for m in memories[-10:]:
                result += "- " + m["fact"] + "\n"
            return result
        except:
            return "Error reading memories"
    
    @kernel_function(
        name="forget_fact",
        description="Delete/forget a specific memory. Use when user says 'forget that' or 'delete memory'"
    )
    def forget_fact(
        self,
        fact_to_forget: Annotated[str, "The fact or keyword to forget/delete from memory"]
    ) -> str:
        """Delete a memory that matches the input."""
        import json
        
        if not os.path.exists(self.MEMORY_FILE):
            return "No memories to forget."
        
        try:
            with open(self.MEMORY_FILE, "r", encoding="utf-8") as f:
                memories = json.load(f)
            
            if not memories:
                return "No memories to forget."
            
            # Find and remove matching memories (fuzzy match)
            keyword = fact_to_forget.lower()
            original_count = len(memories)
            memories = [m for m in memories if keyword not in m["fact"].lower()]
            removed_count = original_count - len(memories)
            
            if removed_count == 0:
                return "No memory found matching '" + fact_to_forget + "'"
            
            # Save updated memories
            with open(self.MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
            
            return "Forgot " + str(removed_count) + " memory(s) about '" + fact_to_forget + "'"
        except Exception as e:
            return "Error: " + str(e)
    
    @kernel_function(
        name="reset_system",
        description="Reset/clear conversation history. Use when user says 'reset system', 'clear history', 'start fresh'"
    )
    def clear_short_term_memory(self) -> str:
        """Clear the conversation history to stop hallucination loops."""
        try:
            # Import and clear the conversation history from brain module
            import brain
            brain.CONVERSATION_HISTORY.clear()
            return "System reset. Conversation history cleared. Starting fresh!"
        except Exception as e:
            return "Reset failed: " + str(e)


# ============================================
# Export all plugin classes
# ============================================

ALL_PLUGINS = [
    WindowsPlugin,
    FileIOPlugin,
    TimePlugin,
    PowerPlugin,
    NetworkPlugin,
    MemoryPlugin,
]

