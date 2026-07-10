@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $lnk = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\Ideabucket.lnk'); $lnk.TargetPath = '%~dp0restart.bat'; $lnk.WorkingDirectory = '%~dp0'; $lnk.IconLocation = '%~dp0ideabucket.ico'; $lnk.Description = 'Start Ideabucket bot'; $lnk.Save(); Write-Host 'Shortcut created on Desktop.'"
timeout /t 3
