@echo off
rem Importa el Excel de clientes depositado en la carpeta entrada/
cd /d "%~dp0"
echo Importando clientes desde entrada\ ...
.venv\Scripts\python.exe scripts\importar_clientes.py
echo Generando el Excel de gestion actualizado...
.venv\Scripts\python.exe scripts\sync.py
echo.
pause
