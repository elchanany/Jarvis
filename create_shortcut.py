import os
from win32com.client import Dispatch

def create_jarvis_shortcut():
    desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
    path = os.path.join(desktop, "Jarvis.lnk")
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    
    pythonw_path = os.path.join(project_dir, "venv", "Scripts", "pythonw.exe")
    script_path = os.path.join(project_dir, "Jarvis.pyw")
    icon_path = os.path.join(project_dir, "static", "logo.ico")
    
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = pythonw_path
    shortcut.Arguments = f'"{script_path}"'
    shortcut.WorkingDirectory = project_dir
    shortcut.IconLocation = icon_path
    shortcut.save()
    
    print(f"✅ Desktop shortcut created: {path}")

if __name__ == "__main__":
    create_jarvis_shortcut()
