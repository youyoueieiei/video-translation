@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  echo Please install Python, then run this launcher again.
  pause
  exit /b 1
)

python -c "import faster_whisper, srt, requests, bs4" >nul 2>nul
if errorlevel 1 (
  echo Installing Python dependencies...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
  )
)

python subtitle_translator_app.py
endlocal
