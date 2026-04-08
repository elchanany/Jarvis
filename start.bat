@echo off
chcp 65001 > nul
title Jarvis AI — Starting...

:: ══════════════════════════════════════════════
::  JARVIS LAUNCHER
::  Opens Jarvis as a native desktop application
:: ══════════════════════════════════════════════

set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%venv"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
set "PIP=%VENV_DIR%\Scripts\pip.exe"

echo.
echo  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
echo  █                                         █
echo  █           J A R V I S                   █
echo  █       AI Personal Assistant             █
echo  █                                         █
echo  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
echo.

:: ── Step 1: Create venv if missing ──
if not exist "%PYTHON%" (
    echo  [1/4] Creating Python virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [ERROR] Python not found! Please install Python 3.10+ from https://python.org
        pause
        exit /b 1
    )
    echo  [1/4] Virtual environment created. ✓
) else (
    echo  [1/4] Virtual environment found. ✓
)

:: ── Step 2: Install / update dependencies ──
echo  [2/4] Checking dependencies...
"%PYTHON%" -m pip install -r "%PROJECT_DIR%requirements.txt" --quiet --no-warn-script-location
if errorlevel 1 (
    echo  [WARNING] Some packages may have failed. Continuing...
) else (
    echo  [2/4] Dependencies OK. ✓
)

:: ── Step 3: Start Flask server in background ──
echo  [3/4] Starting Jarvis server...
start "" /B "%PYTHON%" "%PROJECT_DIR%app.py" > "%PROJECT_DIR%jarvis.log" 2>&1

:: Wait for Flask to be ready
echo  [3/4] Waiting for server...
timeout /t 3 /nobreak > nul

:: ── Step 4: Open as native window ──
echo  [4/4] Opening Jarvis window...
"%PYTHON%" "%PROJECT_DIR%launcher.py"

echo.
echo  Jarvis closed. Goodbye, Sir.
timeout /t 2 /nobreak > nul
