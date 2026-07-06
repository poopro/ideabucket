@echo off
cd /d "%~dp0"
echo Stopping old bot (if any)...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object {$_.CommandLine -match 'bot.main'} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
timeout /t 2 >nul
if not exist .venv\Scripts\activate.bat (
    echo Not installed yet. Please double-click setup.bat first.
    pause
    exit /b
)
call .venv\Scripts\activate.bat
echo Starting Ideabucket bot... (closing this window stops the bot)
python -m bot.main
pause
