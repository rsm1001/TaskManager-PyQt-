@echo off
chcp 65001 > nul 2>&1
cd /d "%~dp0"

echo.
echo Task Manager - PyQt Version
echo ===========================
echo.

set PYTHON_EXE=C:\Users\27185\AppData\Roaming\LobsterAI\runtimes\python-win\python.exe

if not exist "%PYTHON_EXE%" (
    echo Error: Python not found
    pause
    exit /b 1
)

echo Checking dependencies...
"%PYTHON_EXE%" -c "import PyQt6; import sqlalchemy; print('OK')" > nul 2>&1
if errorlevel 1 (
    echo Dependencies not found, installing...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Dependency installation failed
        pause
        exit /b 1
    )
)

echo Starting Task Manager...
"%PYTHON_EXE%" main.py

pause
