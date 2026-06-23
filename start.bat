@echo off
chcp 65001 >nul
echo ================================
echo   AStock Terminal
echo ================================
echo.
echo Starting backend (http://localhost:5000) ...
echo Browser will open automatically.
echo.
"C:\Users\xyc\.workbuddy\binaries\python\envs\default\Scripts\python.exe" "%~dp0server.py"
pause
