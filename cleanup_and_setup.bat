@echo off
echo ==================================================
echo      CLEANUP: Deleting heavy models
echo ==================================================

echo.
echo 1. Deleting faster-whisper model (~500MB)...
if exist "%USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-small" (
    rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--Systran--faster-whisper-small"
    echo    - Deleted faster-whisper-small
) else (
    echo    - Not found (already deleted)
)

echo.
echo 2. Deleting old venv with heavy dependencies...
cd /d "C:\Users\elchanan yehuda\Documents\Jarvis_Project"
if exist venv (
    rmdir /s /q venv
    echo    - Deleted venv
)

echo.
echo 3. Recreating clean venv...
python -m venv venv
call venv\Scripts\activate
pip install openvino-genai speechrecognition pyaudio numpy simpleaudio requests

echo.
echo ==================================================
echo      DONE! Run 'run_jarvis.bat' to start
echo ==================================================
pause
