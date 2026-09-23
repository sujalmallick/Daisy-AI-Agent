@echo off
title Daisy AI Desktop Companion
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo ===================================================
echo   Daisy AI Desktop Companion
echo   Screen Vision + Voice + Spotify MCP
echo ===================================================

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in .\venv
    echo Please make sure Python venv is installed.
    pause
    exit /b 1
)

echo Starting Daisy Desktop Native Window...
.\venv\Scripts\python.exe daisy_app.py

if errorlevel 1 (
    echo.
    echo Daisy closed.
    pause
)
