@echo off
chcp 65001 > nul
cd /d "%~dp0"
title TCM Frontend - Next.js :3000
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
)
call npm run dev
