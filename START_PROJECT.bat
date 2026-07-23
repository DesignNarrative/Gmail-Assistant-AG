@echo off
title Gmail Assistant Launcher
echo ======================================================
echo Starting Gmail Assistant (UNIFIED SINGLE-PROCESS MODE)
echo ======================================================

echo.
echo Starting Application Server (on Port 8000)...
start "Gmail Assistant App" cmd /k "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo Waiting 3 seconds for server to initialize...
ping 127.0.0.1 -n 4 >nul

echo.
echo Opening http://localhost:8000 in browser...
start http://localhost:8000

echo ======================================================
echo Gmail Assistant is running!
echo Do not close this terminal or the child windows.
echo To stop everything, double-click STOP_PROJECT.bat
echo ======================================================
pause
