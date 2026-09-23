@echo off
REM Double-click this file to run VerifyIntern on this computer.
REM It needs Python, free from https://python.org/downloads (tick
REM "Add python.exe to PATH" in the installer).

cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py tools\serve.py
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python tools\serve.py
  ) else (
    echo.
    echo Python was not found on this computer.
    echo Install it from https://python.org/downloads and tick
    echo "Add python.exe to PATH", then double-click this file again.
    echo.
    pause
    exit /b 1
  )
)
pause
