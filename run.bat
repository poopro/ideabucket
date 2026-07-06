@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\activate.bat (
    echo Not installed yet. Please double-click setup.bat first.
    pause
    exit /b
)
call .venv\Scripts\activate.bat
echo Starting Ideabucket bot... (closing this window stops the bot)
python -m bot.main
pause
