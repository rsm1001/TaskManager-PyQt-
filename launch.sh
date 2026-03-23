#!/bin/bash

echo
echo "Task Manager - PyQt Version"
echo "==========================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 not found, please install Python3 first"
    read -p "Press any key to continue..."
    exit 1
fi

echo "Checking dependencies..."
if python3 -c "import PyQt6, sqlalchemy; print('Dependencies check passed')" &> /dev/null; then
    echo "Dependencies already installed"
else
    echo "Dependencies not found, installing..."
    if [ -f "requirements.txt" ]; then
        pip3 install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo "Dependency installation failed"
            read -p "Press any key to continue..."
            exit 1
        fi
    else
        echo "requirements.txt not found"
        read -p "Press any key to continue..."
        exit 1
    fi
fi

echo "Starting Task Manager..."
python3 main.py

read -p "Press any key to continue..."