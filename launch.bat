@echo off
chcp 65001 > nul 2>&1
setlocal
title Task Manager

cd /d "%~dp0"

echo.
echo Task Manager - PyQt Version
echo ===========================
echo.

if not exist "%~dp0.venv\Scripts\python.exe" (
    where py > nul 2>&1
    if not errorlevel 1 (
        echo Creating project virtual environment with py...
        py -3 -m venv .venv
    )
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Retrying virtual environment creation with python...
    python -m venv .venv
)

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo 请安装 Python 3.8+ 并加入 PATH
    exit /b 1
)

"%~dp0.venv\Scripts\python.exe" -c "import sys; raise SystemExit(sys.version_info < (3, 8))" > nul 2>&1
if errorlevel 1 (
    echo 请安装 Python 3.8+ 并加入 PATH
    exit /b 1
)

echo Installing dependencies...
rem Bypass an invalid Windows/user proxy only for this setlocal launch session.
set "NO_PROXY=*"
set "no_proxy=*"
"%~dp0.venv\Scripts\python.exe" -m pip install --isolated -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo Dependency installation failed.
    exit /b 1
)

echo Starting Task Manager...
"%~dp0.venv\Scripts\python.exe" main.py
endlocal
