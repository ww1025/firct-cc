@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   礼服自动分配 - 直接生成Excel
echo ========================================
echo.
echo   正在读取上月数据 + 排班表...
echo.

python "%~dp0build.py"

echo.
echo ========================================
echo   已生成: 本月礼服分配.xlsx
echo   路径: %~dp0本月礼服分配.xlsx
echo ========================================
echo.

start "" "%~dp0本月礼服分配.xlsx"

pause
