@echo off
chcp 65001 >nul
echo ================================
echo   AStock Terminal Backend
echo ================================
echo.
echo Starting Python backend (http://localhost:5000) ...
echo.
"C:\Users\HP\.workbuddy\binaries\python\envs\default\Scripts\python.exe" "%~dp0server.py"
pause
