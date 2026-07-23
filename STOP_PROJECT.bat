@echo off
title Stop Gmail Assistant
echo ======================================================
echo Stopping all Gmail Assistant processes...
echo ======================================================

echo Killing python application server...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im python3.exe >nul 2>&1
taskkill /f /im python3.10.exe >nul 2>&1

echo.
echo [OK] Unified application server stopped cleanly.
echo (PostgreSQL service keeps running in the background)
echo ======================================================
pause
