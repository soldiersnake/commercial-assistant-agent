@echo off
rem CORRIDA AUTOMATICA (la llaman las tareas programadas de 7:00 y 16:00)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\corrida.ps1" -Silencioso
