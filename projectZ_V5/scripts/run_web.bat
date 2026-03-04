@echo off
REM run_web.bat - start the front-end application (version 5.0)

REM move to repository root first
PUSHD "%~dp0\..\.."
PUSHD "projectZ_V5"
CALL ".venv\Scripts\activate.bat"
python app.py
POPD
POPD
