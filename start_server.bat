@echo off
chcp 65001 > nul
cd /d "%~dp0"
title 出荷伝票サーバー

echo ============================================
echo   出荷伝票アプリ サーバー起動
echo ============================================
echo.

:: --- Python3 で試す ---
python3 --version > nul 2>&1
if %errorlevel% == 0 (
    echo [Python3] で起動します...
    python3 start_server.py
    goto end
)

:: --- python で試す ---
python --version > nul 2>&1
if %errorlevel% == 0 (
    echo [Python] で起動します...
    python start_server.py
    goto end
)

:: --- Node.js で試す ---
node --version > nul 2>&1
if %errorlevel% == 0 (
    echo [Node.js] で起動します...
    node start_server_node.js
    goto end
)

:: --- PowerShell で試す（Windowsに必ず入っている）---
echo [PowerShell] で起動します...
powershell -ExecutionPolicy Bypass -File "%~dp0start_server.ps1"
goto end

:end
pause
