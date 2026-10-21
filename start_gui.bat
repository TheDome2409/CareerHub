@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=%CD%\src
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run src\jobagent\ui\streamlit_app.py --server.address 127.0.0.1
) else (
    py -3.12 -m streamlit run src\jobagent\ui\streamlit_app.py --server.address 127.0.0.1
)
exit /b %errorlevel%
