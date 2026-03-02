@echo off
REM setup_production.bat - prepare a production-style environment on Windows

REM This script creates Python virtual environments and installs all required
REM packages defined in full_requirements.txt.  It also copies the example
REM configuration files into place.  It does NOT register Windows services.

setlocal enabledelayedexpansion

REM move to repo root
cd /d "%~dp0"
cd ..\

ECHO Creating combined virtual environment (.venv-all)...
if not exist ".venv-all" (
    python -m venv .venv-all
)
CALL ".venv-all\Scripts\activate.bat"
pip install --upgrade pip
if exist "full_requirements.txt" (
    pip install -r full_requirements.txt
) else (
    echo full_requirements.txt not found, skipping package installation.
)
CALL deactivate

ECHO Copying configuration templates...
if exist "internal api\.env.example" (
    if not exist "internal api\.env" copy "internal api\.env.example" "internal api\.env"
)
if exist "projectz v3\.env.example" (
    if not exist "projectz v3\.env" copy "projectz v3\.env.example" "projectz v3\.env"
)

ECHO.
ECHO Production setup steps completed.  Edit the new .env files with real values,
ECHO then install the services manually (e.g. using nssm, sc.exe or Task Scheduler).
ECHO See PRODUCTION_SETUP.md for detailed instructions.

endlocal
