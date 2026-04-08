@echo off
echo ==================================================
echo      CLEAN REINSTALL OF JARVIS ENV
echo ==================================================
echo.
echo 1. Deleting old virtual environment...
if exist venv (
    rmdir /s /q venv
    echo    - Deleted old venv.
)

echo.
echo 2. Creating new virtual environment...
python -m venv venv
echo    - Created venv.

echo.
echo 3. Installing Faster-Whisper (Active CPU Mode)...
call venv\Scripts\activate
pip install faster-whisper speechrecognition pyaudio simpleaudio numpy
echo    - Installation complete.

echo.
echo ==================================================
echo      STARTING JARVIS
echo ==================================================
python main.py
pause
