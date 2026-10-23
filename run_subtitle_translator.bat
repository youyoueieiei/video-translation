@echo off
REM Double-click: open GUI only. Optional: drop an MP4 onto this file to pre-fill it.
cd /d "%~dp0"

where pythonw >nul 2>nul
if errorlevel 1 goto :use_python

if "%~1"=="" (
  start "" /D "%~dp0" pythonw "%~dp0subtitle_translator_app.py"
) else (
  start "" /D "%~dp0" pythonw "%~dp0subtitle_translator_app.py" "%~1"
)
exit /b 0

:use_python
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10+ and check "Add to PATH".
  pause
  exit /b 1
)
if "%~1"=="" (
  start "" /D "%~dp0" python "%~dp0subtitle_translator_app.py"
) else (
  start "" /D "%~dp0" python "%~dp0subtitle_translator_app.py" "%~1"
)
exit /b 0
