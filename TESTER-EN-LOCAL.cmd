@echo off
chcp 65001 >nul
echo Lancement du site en local sur http://localhost:8080/ ...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\serveur-local.ps1"
pause
