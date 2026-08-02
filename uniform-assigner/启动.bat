@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   礼服自动分配系统
echo ========================================
echo.
echo   启动后打开浏览器访问: http://localhost:8765
echo   关闭此窗口即停止服务
echo.

start http://localhost:8765

python server.py

pause
