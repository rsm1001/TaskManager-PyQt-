@echo off
chcp 65001 > nul 2>&1
title 任务管理系统
set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"
cd /d "%PROJECT_ROOT%"

echo.
echo Task Manager - PyQt Version
echo ===========================
echo.

if not exist "%PYTHON_EXE%" (
    echo Creating project virtual environment...
    py -3 -m venv .venv > nul 2>&1
    if errorlevel 1 (
        python -m venv .venv > nul 2>&1
    )

    if not exist "%PYTHON_EXE%" (
        echo Failed to create the project virtual environment.
        echo 请安装 Python 3.8+ 并加入 PATH
        pause
        exit /b 1
    )
)

"%PYTHON_EXE%" -c "import sys; raise SystemExit(sys.version_info < (3, 8))" > nul 2>&1
if errorlevel 1 (
    echo 请安装 Python 3.8+ 并加入 PATH
    pause
    exit /b 1
)

echo Installing dependencies...
"%PYTHON_EXE%" -m pip install -r "%PROJECT_ROOT%requirements.txt"
if errorlevel 1 (
    echo Dependency installation failed
    pause
    exit /b 1
)

echo Starting Task Manager...
"%PYTHON_EXE%" main.py

pause
