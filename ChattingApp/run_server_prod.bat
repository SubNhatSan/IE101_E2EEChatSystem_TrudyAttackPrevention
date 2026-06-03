@echo off
chcp 65001 > nul
cls
echo ===============================================
echo   WEB CHAT SERVER - Production (Gunicorn)
echo ===============================================
echo.

cd /d "%~dp0\webapp"

REM Check if venv exists
if not exist "..\env\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    pause
    exit /b 1
)

REM Check if gunicorn is installed
..\env\Scripts\pip.exe show gunicorn > nul 2>&1
if errorlevel 1 (
    echo [*] Installing gunicorn...
    ..\env\Scripts\pip.exe install gunicorn==21.2.0
)

echo [+] Starting server with Gunicorn
echo [+] Workers: 4
echo [+] Access: http://YOUR_IP:5000
echo.
echo Press CTRL+C to stop the server
echo.

..\env\Scripts\gunicorn.exe -w 4 -b 0.0.0.0:5000 --timeout 120 app:app

pause
