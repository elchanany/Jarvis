@echo off
echo 🛠️ Installing System Control Dependencies...
echo ------------------------------------------

echo 1. Installing pycaw (Volume Control)...
call venv\Scripts\python -m pip install pycaw comtypes

echo 2. Installing pyautogui (Media/App Control)...
call venv\Scripts\python -m pip install pyautogui

echo.
echo ✅ Installation Complete.
echo You can now proceed with the update.
pause
