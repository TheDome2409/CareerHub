@echo off

cd /d "%~dp0"

set PYTHONPATH=%CD%\src

rem wkhtmltopdf in PATH aufnehmen
set PATH=%PATH%;C:\Program Files\wkhtmltopdf\bin

py -m streamlit run src\jobagent\ui\streamlit_app.py