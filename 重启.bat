@echo off
title LuxeLocks Hub
cd /d C:\Users\HUAWEI\luxelocks-hub

echo ===================================
echo   LuxeLocks Hub
echo ===================================
echo.

:: Kill existing python
taskkill /f /im python.exe >nul 2>nul
echo Old process killed.
timeout /t 1 /nobreak >nul

:: Start server
echo Starting server...
start "LuxeLocksHub" /min cmd /c "cd /d C:\Users\HUAWEI\luxelocks-hub && python app.py"
timeout /t 3 /nobreak >nul

:: Open browser
start http://localhost:8001

echo.
echo Hub running at http://localhost:8001
echo Close this window or keep it open.
pause
