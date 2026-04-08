@echo off
echo ============================================
echo   🧹 Jarvis - Disk Cleanup Script (Updated)
echo   Freeing ~2-3GB for Qwen2.5 download
echo ============================================
echo.
echo This will delete:
echo   - kokoro-onnx (duplicate TTS - not used)
echo   - whisper_openvino_small (old STT version)
echo   - model_cache (temp files - will regenerate)
echo.
echo Keeping:
echo   - phi4-mini (backup LLM)
echo   - kokoro-intel (active TTS in main.py)
echo   - whisper-small-he-openvino (active STT)
echo   - ask.py-main (small project)
echo.

pause

cd /d "c:\Users\elchanan yehuda\Documents\Jarvis_Project"

echo.
echo [1/3] Deleting kokoro-onnx (duplicate)...
rmdir /s /q "models\kokoro-onnx" 2>nul
if %errorlevel% == 0 (echo    ✓ Deleted) else (echo    - Not found)

echo [2/3] Deleting whisper_openvino_small (old)...
rmdir /s /q "whisper_openvino_small" 2>nul
if %errorlevel% == 0 (echo    ✓ Deleted) else (echo    - Not found)

echo [3/3] Deleting model_cache (temp)...
rmdir /s /q "model_cache" 2>nul
if %errorlevel% == 0 (echo    ✓ Deleted) else (echo    - Not found)

echo.
echo ============================================
echo   ✅ Cleanup Complete!
echo   You should now have ~2-3GB free
echo ============================================
echo.
echo Next: Run download_qwen.bat
pause
