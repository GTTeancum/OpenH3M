@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0.local\tools\Run-Warlock.ps1"
if errorlevel 1 pause
