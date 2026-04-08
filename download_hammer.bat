@echo off
echo ============================================
echo   Hammer 2.1 (3B) LAM - Setup Script
echo ============================================
echo.

cd /d "c:\Users\elchanan yehuda\Documents\Jarvis_Project"
call venv\Scripts\activate

echo [1/2] Installing dependencies...
pip install -U pip
pip install -U optimum[openvino] transformers onnx nncf

echo.
echo [2/2] Downloading and Converting model (takes 10-20 min)...
python convert_hammer.py

echo.
echo ============================================
echo   DONE! Hammer is now installed.
echo ============================================
pause
