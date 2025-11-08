@echo off
cd /d "%~dp0"
title DALI Voice Assistant - Complete System
color 0A

echo.
echo ============================================
echo 🚀 Starting DALI Voice Assistant (Full System)
echo ============================================
echo.

REM 1️⃣ Activate virtual environment (env instead of venv)
if exist ".\env\Scripts\activate" (
    call .\env\Scripts\activate
    echo ✅ Activated virtual environment
) else (
    echo ❌ Virtual environment 'env' not found!
    pause
    exit /b
)

echo.

REM 2️⃣ Navigate to Rasa folder and train if needed
cd backend\rasa

set modelFound=
for /f "delims=" %%i in ('dir /b /a-d models\*.tar.gz 2^>nul') do set modelFound=1

if not defined modelFound (
    echo 🧠 Training Rasa model...
    rasa train
)

echo ✅ Rasa model ready
echo.

REM 3️⃣ Start Rasa Action Server
echo 🧩 Starting Rasa Action Server (port 5055)
start "Rasa Actions" cmd /k "cd /d %~dp0backend\rasa && call ..\..\env\Scripts\activate && rasa run actions"
timeout /t 3 >nul

REM 4️⃣ Start Rasa Core Server
echo 🤖 Starting Rasa Server (port 5005)
start "Rasa Server" cmd /k "cd /d %~dp0backend\rasa && call ..\..\env\Scripts\activate && rasa run --enable-api --cors *"
timeout /t 5 >nul

REM 5️⃣ Navigate back to root
cd ..\..

REM 6️⃣ Start Voice Assistant (Optional - comment out if not needed)
echo 🎙️ Starting DALI Voice Assistant
start "DALI Voice" cmd /k "cd /d %~dp0 && call env\Scripts\activate && python main.py"
timeout /t 2 >nul

REM 7️⃣ Start WebSocket Server
echo 🔌 Starting WebSocket Server (port 8765)
start "WebSocket Server" cmd /k "cd /d %~dp0 && call env\Scripts\activate && python backend\websocket_server.py"
timeout /t 2 >nul

REM 8️⃣ Start Flask Web Server
echo 🌐 Starting Web Interface (port 5000)
start "Web Server" cmd /k "cd /d %~dp0 && call env\Scripts\activate && python app.py"
timeout /t 3 >nul

REM 9️⃣ Open browser
start http://localhost:5000

echo.
echo ============================================
echo ✅ All Systems Running!
echo ============================================
echo.
echo 🧩 Rasa Actions      → http://localhost:5055
echo 🤖 Rasa Server       → http://localhost:5005
echo 🎙️ Voice Assistant   → Console window
echo 🔌 WebSocket Server  → ws://localhost:8765
echo 🌐 Web Interface     → http://localhost:5000
echo.
echo Five windows opened. Browser will open automatically.
echo.
pause
