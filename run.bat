@echo off
setlocal
echo ==================================================================
echo   CottonVision - UAV Cotton ^& Weed Detection System
echo ==================================================================
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python was not found in your PATH.
    echo Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import flask, werkzeug, cv2, ultralytics" >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing dependencies from requirements.txt...
    python -m pip install -r requirements.txt
)

echo Starting CottonVision server on http://localhost:5000 ...
set PYTHONPATH=%~dp0
start http://localhost:5000
python -m backend.server.server
pause
