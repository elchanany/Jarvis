@echo off
echo ============================================
echo   Qwen2.5-3B (INT4) - Setup Script
echo ============================================
echo.

cd /d "c:\Users\elchanan yehuda\Documents\Jarvis_Project"
call venv\Scripts\activate

echo [1/2] Installing dependencies...
pip install -U pip
pip install -U optimum[openvino] transformers onnx nncf

echo.
echo [2/2] Converting model (takes 5-10 min)...
python convert_qwen.py

echo.
echo ============================================
echo   DONE! Test with: python test_llm.py
echo ============================================
pause
