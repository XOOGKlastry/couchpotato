@echo off
cd /d "%~dp0"
if exist couchpotato.exe (
    couchpotato.exe
    exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 app.py
    pause
    exit /b
)
echo Pobierz couchpotato.exe ze strony aplikacji.
pause
