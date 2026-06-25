@echo off
title LuxeLocks Hub
echo ===================================
echo   LuxeLocks Hub - 启动中
echo ===================================
echo.
echo 启动 API 服务器...
start "" "LuxeLocks Hub Server" cmd /c "cd /d C:\Users\HUAWEI\luxelocks-hub && python app.py"
timeout /t 3 /nobreak >nul 2>nul
echo 打开看板...
start http://localhost:8001
echo.
echo ===================================
echo   启动完成
echo   看板: http://localhost:8001
echo   按任意键退出此窗口...
echo ===================================
pause >nul
