@echo off
title Daisy AI Voice Assistant
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"
cd /d "%~dp0"

echo ===================================================
echo   Daisy Desktop Voice Assistant
echo   NVIDIA RTX 3050 CUDA Engine + Spotify MCP
echo ===================================================
if "%1"=="--rebuild" goto DO_BUILD
if exist "desktop\src-tauri\target\release\daisy.exe" goto RUN_APP

:DO_BUILD
echo Building the current Daisy desktop UI...
pushd desktop
call npm run build
if errorlevel 1 (
	echo Desktop UI build failed.
	popd
	pause
	exit /b 1
)
echo Building the transparent native Tauri window...
call npx tauri build
if errorlevel 1 (
	echo Tauri build failed. Ensure Rust and the Tauri CLI are installed.
	popd
	pause
	exit /b 1
)
popd

:RUN_APP
echo Starting Daisy FastAPI backend server...
start /B "" venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --log-level warning
timeout /t 2 /nobreak >nul
echo Launching Daisy transparent Tauri desktop window...
desktop\src-tauri\target\release\daisy.exe

pause
