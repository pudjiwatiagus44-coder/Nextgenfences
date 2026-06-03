@echo off
cd /d "%~dp0"
echo Starting NextGen Desktop...
python main.py
if %errorlevel% neq 0 (
    echo Error occurred!
    pause
)
