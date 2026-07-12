@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
echo === Ideabucket setup ===

set PY=
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys; raise SystemExit(sys.version_info < (3,10))" >nul 2>nul
    if not errorlevel 1 set PY=py -3.12
)
if not defined PY (
    where python >nul 2>nul
    if not errorlevel 1 (
        python -c "import sys; raise SystemExit(sys.version_info < (3,10))" >nul 2>nul
        if not errorlevel 1 set PY=python
    )
)
if not defined PY (
    where winget >nul 2>nul
    if errorlevel 1 (
        echo Python 3.10 or newer and winget were not found.
        echo Please install Python 3.12 from https://python.org and run setup.bat again.
        pause
        exit /b 1
    )
    echo Compatible Python not found. Installing Python 3.12 via winget...
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo Python installation failed.
        pause
        exit /b 1
    )
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
if exist requirements.lock (
    python -m pip install --quiet -r requirements.lock
) else (
    python -m pip install --quiet -r requirements.txt
)
if errorlevel 1 (
    echo Package install failed. Check your internet connection.
    pause
    exit /b
)

echo [3/3] Preparing .env config...
if not exist .env copy .env.example .env >nul

for /f "delims=" %%T in ('powershell -NoProfile -Command "$rng=[Security.Cryptography.RandomNumberGenerator]::Create();$b=New-Object byte[] 32;$rng.GetBytes($b);[Convert]::ToBase64String($b).TrimEnd('=').Replace('+','-').Replace('/','_')"') do set CAPTURE_TOKEN=%%T
set CAPTURE_PORT=8787
for /f "tokens=1,* delims==" %%A in ('findstr /B /C:"CAPTURE_PORT=" .env') do if not "%%B"=="" set CAPTURE_PORT=%%B
findstr /B /C:"CAPTURE_TOKEN=" .env >nul
if errorlevel 1 (
    echo CAPTURE_TOKEN=!CAPTURE_TOKEN!>>.env
) else (
    powershell -NoProfile -Command "$p='.env';$c=Get-Content $p;$c=$c -replace '^CAPTURE_TOKEN=.*$','CAPTURE_TOKEN=!CAPTURE_TOKEN!';Set-Content -Encoding UTF8 $p $c"
)
(
    echo self.IDEABUCKET_ENDPOINT = "http://127.0.0.1:!CAPTURE_PORT!/capture";
    echo self.IDEABUCKET_CAPTURE_TOKEN = "!CAPTURE_TOKEN!";
)>extension\config.js

echo.
echo === Setup complete! ===
echo Notepad will now open .env - fill in these three values:
echo    TELEGRAM_BOT_TOKEN   ^(Telegram: @BotFather, send /newbot^)
echo    TELEGRAM_OWNER_USER_ID ^(your numeric ID from @userinfobot^)
echo    OPENROUTER_API_KEY   ^(https://openrouter.ai/keys^)
echo Save the file, close Notepad, then double-click run.bat
echo.
start notepad .env
timeout /t 15
