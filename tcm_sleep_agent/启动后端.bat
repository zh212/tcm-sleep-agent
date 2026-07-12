@echo off
chcp 65001 > nul
cd /d "%~dp0"
title TCM Backend - FastAPI :8000
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found.
    echo Run: py -3.12 -m venv .venv
    echo Then: .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000 --host 127.0.0.1
