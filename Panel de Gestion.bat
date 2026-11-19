@echo off
rem Abre el Panel de Gestion (servidor local + navegador)
cd /d "%~dp0"
start "Panel - servidor local" /MIN .venv\Scripts\python.exe dashboard\servidor.py
timeout /t 1 /nobreak >nul
start "" http://127.0.0.1:8765
