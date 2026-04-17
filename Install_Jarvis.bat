@echo off
chcp 65001 >nul
title Jarvis AI - Installer

echo ========================================================
echo         Jarvis AI - Initialization
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed.
    echo Please download and install Python. Make sure to check "Add Python to PATH".
    echo.
    echo Opening download page...
    start https://www.python.org/downloads/
    pause
    exit /b
)

:: 2. Create Virtual Environment
if not exist "venv\Scripts\python.exe" (
    echo Creating virtual environment VENV for smooth installation...
    python -m venv venv
)

:: 3. Install core boot dependencies
call "venv\Scripts\activate.bat"
python -c "import flask, webview, requests, psutil, langchain_core" >nul 2>&1
if errorlevel 1 (
    echo Preparing visual UI, this may take 30 seconds to download dependencies...
    python -m pip install -q -r requirements.txt
) else (
    echo Visual UI is ready...
)

:: 4. Start the Application / Setup wizard
echo Launching rich setup wizard...
start "" "venv\Scripts\pythonw.exe" Jarvis.pyw

exit
