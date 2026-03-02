@echo off
REM run_web.bat - start the front‑end application

REM move to repo root first
PUSHD "%~dp0\..\.."
PUSHD "projectz v3"
CALL ".venv\Scripts\activate.bat"
python app.py
POPD
POPD
