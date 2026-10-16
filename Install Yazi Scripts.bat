@echo off
setlocal

cd /d "%~dp0"

echo Starting combined Yazi setup and launcher installer...
echo.

"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%~dp0yazi-installer.ps1" -InstallYazi -InstallDependencies %*
set "result=%ERRORLEVEL%"

echo.
echo Installer exited with code %result%.
echo Review any messages above before closing this window.
echo.
pause
exit /b %result%
