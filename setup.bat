@echo off
cd /d "%~dp0"
echo === Ideabucket setup ===

set PY=
where py >nul 2>nul
if not errorlevel 1 set PY=py
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 set PY=python
)
if not defined PY (
    echo Python not found. Installing via winget...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    echo.
    echo Python installed. Please CLOSE this window and double-click setup.bat AGAIN.
    pause
    exit /b
)

echo [1/3] Creating virtual environment...
%PY% -m venv .venv
if errorlevel 1 (
    echo Failed to create venv.
    pause
    exit /b
)

echo [2/3] Installing packages...
call .venv\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo Package install failed. Check your internet connection.
    pause
    exit /b
)

echo [3/3] Preparing .env config...
if not exist .env copy .env.example .env >nul

echo.
echo === Setup complete! ===
echo Notepad will now open .env - paste your two keys after the equals signs:
echo    TELEGRAM_BOT_TOKEN   ^(Telegram: @BotFather, send /newbot^)
echo    OPENROUTER_API_KEY   ^(https://openrouter.ai/keys^)
echo Save the file, close Notepad, then double-click run.bat
echo.
start notepad .env
timeout /t 15
