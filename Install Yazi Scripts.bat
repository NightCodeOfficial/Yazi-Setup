@echo off
setlocal

cd /d "%~dp0"

echo Starting Yazi Windows Scripts installer...
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0yazi-installer.ps1"

echo.
echo Installer finished.
echo Review any messages above before closing this window.
echo.
pause
