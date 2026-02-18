@echo off
REM RedactQC - Double-click to set up and run
REM This wrapper launches the PowerShell setup script with bypass execution policy
powershell -ExecutionPolicy Bypass -File "%~dp0setup-and-run.ps1"
pause
