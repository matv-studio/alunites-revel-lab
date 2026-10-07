@echo off
chcp 65001 >nul
echo Telechargement des medias du site alunites.com (environ 430 fichiers, ~440 Mo)...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0_import\telecharger-medias.ps1"
echo.
pause
