@echo off
setlocal EnableDelayedExpansion
title Gmail Assistant - Director PC Installer
color 0B

echo ==========================================================
echo   Abhinav Group - AI Gmail Assistant
echo   One-time installer for the Director's PC
echo ==========================================================
echo.
echo This script will:
echo   1. Check that Python, PostgreSQL, Tesseract and Poppler exist
echo   2. Create the database and enable pgvector
echo   3. Write backend\.env for this machine
echo   4. Install all Python packages (needs internet)
echo   5. Create the database tables
echo.
echo After it finishes, just double-click START_PROJECT.bat
echo ==========================================================
echo.
pause

REM Run from the project root (this script lives in director-setup\)
cd /d "%~dp0.."

REM ----------------------------------------------------------
REM 1. Prerequisite checks
REM ----------------------------------------------------------
echo.
echo [1/5] Checking prerequisites...

where python >nul 2>&1
if errorlevel 1 (
    echo   [X] Python not found. Install Python 3.10 or 3.11 from python.org
    echo       IMPORTANT: tick "Add python.exe to PATH" during install.
    goto :fail
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Python %%v

where psql >nul 2>&1
if errorlevel 1 (
    echo   [X] PostgreSQL (psql) not found in PATH.
    echo       Install PostgreSQL 16 from enterprisedb.com, then add
    echo       "C:\Program Files\PostgreSQL\16\bin" to PATH.
    goto :fail
)
echo   [OK] PostgreSQL client found

where tesseract >nul 2>&1
if errorlevel 1 (
    echo   [!] WARNING: Tesseract OCR not found. Scanned files will not be readable.
    echo       Install from: github.com/UB-Mannheim/tesseract/wiki  (then re-run)
) else (
    echo   [OK] Tesseract OCR found
)

where pdftoppm >nul 2>&1
if errorlevel 1 (
    echo   [!] WARNING: Poppler not found. Scanned PDFs will not be readable.
    echo       Download poppler for Windows and add its bin folder to PATH.
) else (
    echo   [OK] Poppler found
)

REM ----------------------------------------------------------
REM 2. Database setup
REM ----------------------------------------------------------
echo.
echo [2/5] Database setup
set /p PGPASS=  Enter the PostgreSQL password chosen during install: 
set PGPASSWORD=%PGPASS%

psql -U postgres -h localhost -c "SELECT 1;" >nul 2>&1
if errorlevel 1 (
    echo   [X] Could not connect to PostgreSQL with that password.
    echo       Make sure the PostgreSQL service is running and the password is correct.
    goto :fail
)
echo   [OK] Connected to PostgreSQL

psql -U postgres -h localhost -tc "SELECT 1 FROM pg_database WHERE datname='gmail_assistant'" | findstr 1 >nul 2>&1
if errorlevel 1 (
    psql -U postgres -h localhost -c "CREATE DATABASE gmail_assistant;" >nul
    echo   [OK] Database "gmail_assistant" created
) else (
    echo   [OK] Database "gmail_assistant" already exists
)

psql -U postgres -h localhost -d gmail_assistant -c "CREATE EXTENSION IF NOT EXISTS vector;" >nul 2>&1
if errorlevel 1 (
    echo   [X] Could not enable the pgvector extension.
    echo       Install pgvector for Windows first (see SETUP_GUIDE), then re-run.
    goto :fail
)
echo   [OK] pgvector extension enabled

REM ----------------------------------------------------------
REM 3. Write backend\.env from the template
REM ----------------------------------------------------------
echo.
echo [3/5] Writing backend\.env ...
powershell -NoProfile -Command "$p = $env:PGPASSWORD; $u = [uri]::EscapeDataString($p); (Get-Content 'director-setup\env.director' -Raw).Replace('__PGPASS_URL__', $u).Replace('__PGPASS__', $p) | Set-Content 'backend\.env' -Encoding UTF8"
if errorlevel 1 (
    echo   [X] Failed to write backend\.env
    goto :fail
)
echo   [OK] backend\.env written

REM ----------------------------------------------------------
REM 4. Python environment + packages
REM ----------------------------------------------------------
echo.
echo [4/5] Installing Python packages (this can take 10-20 minutes)...
cd backend
if not exist venv (
    python -m venv venv
    echo   [OK] Virtual environment created
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo   [X] Package installation failed. Check your internet connection and re-run.
    cd ..
    goto :fail
)
echo   [OK] All packages installed

REM ----------------------------------------------------------
REM 5. Create database tables
REM ----------------------------------------------------------
echo.
echo [5/5] Creating database tables...
python -m alembic upgrade head
if errorlevel 1 (
    echo   [X] Database migration failed. See the error above.
    cd ..
    goto :fail
)
cd ..
echo   [OK] Database ready

echo.
echo ==========================================================
echo   INSTALLATION COMPLETE!
echo ==========================================================
echo.
echo   Next steps:
echo     1. Double-click START_PROJECT.bat
echo     2. At http://localhost:8000 click "Sign up" and create the
echo        account with:
echo          Email: gkankariya@gmail.com
echo          Password: your own choice (keep it safe)
echo        From the next day, simply "Sign in".
echo     3. Click "Connect Gmail" and approve access
echo     4. In Gmail, add the label "Director's AI Assistant"
echo        to the emails the assistant should know about
echo     5. Click "Update emails" in the app
echo.
pause
exit /b 0

:fail
echo.
echo ==========================================================
echo   INSTALLATION STOPPED - fix the issue above and re-run.
echo ==========================================================
pause
exit /b 1
