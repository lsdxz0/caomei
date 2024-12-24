@echo off
echo Starting PDF Processor...
python src/main.py
if errorlevel 1 (
    echo Error occurred! 
    pause
)
