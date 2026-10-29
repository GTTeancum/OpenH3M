@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\Run-CustomMaps.ps1" %*
if errorlevel 1 pause
