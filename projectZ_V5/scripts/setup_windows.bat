@echo off
REM setup_windows.bat - prepare development environments for both services (version 5.0)

REM change to repository root (one level up from this script)
PUSHD "%~dp0\.." 

SETLOCAL ENABLEDELAYEDEXPANSION

ECHO.
ECHO ===== internal api =====
PUSHD "..\internal api"
IF NOT EXIST ".venv" (
    python -m venv .venv
)
CALL ".venv\Scripts\activate.bat"
pip install --upgrade pip
pip install -r requirements.txt
IF NOT EXIST ".env" (
    copy .env.example .env
)
CALL deactivate
POPD

ECHO.
ECHO ===== web application =====
PUSHD "..\projectZ_V5"
IF NOT EXIST ".venv" (
    python -m venv .venv
)
CALL ".venv\Scripts\activate.bat"
pip install --upgrade pip
pip install -r requirements.txt
IF NOT EXIST ".env" (
    copy .env.example .env
)
CALL deactivate
POPD

ECHO.
ECHO Setup complete.  Edit the newly created .env files in each folder before running the services.
ECHO You can then use run_api.bat and run_web.bat to start each component.

POPD
