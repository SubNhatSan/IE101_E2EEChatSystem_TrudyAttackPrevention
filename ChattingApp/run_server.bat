@echo off
chcp 65001 > nul
cls
echo ===============================================
echo   WEB CHAT SERVER - Production Mode
echo ===============================================
echo.

cd /d "%~dp0\webapp"

REM Check if venv exists
if not exist "..\env\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please run setup first.
    pause
    exit /b 1
)

REM Run server
echo [+] Starting server on http://0.0.0.0:5000
echo [+] Local access: http://localhost:5000
echo [+] Network access: http://YOUR_IP:5000
echo.
echo [+] To find your IP, open Command Prompt and run: ipconfig
echo [+] Look for "IPv4 Address" under your network adapter
echo.
echo Press CTRL+C to stop the server
echo.

..\env\Scripts\python.exe app.py

pause
