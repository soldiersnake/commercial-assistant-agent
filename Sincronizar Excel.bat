@echo off
rem Sincroniza el Excel de gestion desde la memoria de datos
cd /d "%~dp0"
echo Sincronizando Excel de gestion...
.venv\Scripts\python.exe scripts\sync.py
echo.
pause
