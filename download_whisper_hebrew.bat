@echo off
echo ============================================
echo   Converting Whisper Hebrew (Stateful + Tokenizers)
echo ============================================
echo.

cd /d "c:\Users\elchanan yehuda\Documents\Jarvis_Project"
call venv\Scripts\activate

echo [1/3] Updating dependencies (adding openvino-tokenizers)...
pip install -U pip
pip install -U optimum-intel[openvino] nncf transformers onnx openvino-tokenizers

echo.
echo [2/3] Running Python Conversion Script...
python convert_stateful.py

echo.
echo [3/3] Checking output (Looking for openvino_detokenizer.xml)...
dir models\whisper-small-he-openvino

echo.
echo ============================================
echo   DONE! Now try test_stt.py
echo ============================================
pause
