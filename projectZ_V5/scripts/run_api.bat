@echo off
REM run_api.bat - start the internal API service using its virtual environment (version 5.0)

REM move to repository root first
PUSHD "%~dp0\..\.."
PUSHD "internal api"
CALL ".venv\Scripts\activate.bat"
python run.py
POPD
POPD
