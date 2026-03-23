@echo off
chcp 65001 > nul
setlocal

echo.
echo Task Manager - PyQt Version
echo ===========================
echo.

rem Check if Python is installed
python --version > nul 2>&1
if errorlevel 1 (
 echo Error: Python not found, please install Python first
 pause
 exit /b 1
)

rem Check dependencies
echo Checking dependencies...
python -c "import sys; import PyQt6; import sqlalchemy; print('Dependencies check passed')" > nul 2>&1
if errorlevel 1 (
 echo Dependencies not found, installing...
 pip install -r requirements.txt
 if errorlevel 1 (
 echo Dependency installation failed
 pause
 exit /b 1
 )
)

rem Run main program
echo Starting Task Manager...
python main.py

pause