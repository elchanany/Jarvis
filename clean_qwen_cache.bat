@echo off
echo ============================================
echo   🧹 Cleaning Qwen Cache
echo ============================================
echo.
echo This will delete:
echo   - Hugging Face cache for Qwen model (~5-6GB)
echo   - Empty qwen-3b-openvino-int4 folder
echo.

pause

echo.
echo [1/2] Deleting Hugging Face cache...
rmdir /s /q "%USERPROFILE%\.cache\huggingface\hub\models--Qwen--Qwen2.5-3B-Instruct" 2>nul
if %errorlevel% == 0 (echo    ✓ Deleted) else (echo    - Not found)

echo [2/2] Deleting output folder...
cd /d "c:\Users\elchanan yehuda\Documents\Jarvis_Project"
rmdir /s /q "models\qwen-3b-openvino-int4" 2>nul
if %errorlevel% == 0 (echo    ✓ Deleted) else (echo    - Not found)

echo.
echo ============================================
echo   ✅ Cache Cleaned! (~5-6GB freed)
echo   Now run: download_qwen.bat
echo ============================================
pause
