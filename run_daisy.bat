@echo off
title Daisy AI Voice Assistant
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo ===================================================
echo   Daisy Desktop Voice Assistant
echo   NVIDIA RTX 3050 CUDA Engine + Spotify MCP
echo ===================================================
echo Starting Daisy native desktop app...

venv\Scripts\python.exe daisy_app.py

pause
