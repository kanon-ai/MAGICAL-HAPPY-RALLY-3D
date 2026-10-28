@echo off
cd /d "%~dp0"
python tools\play.py %*
if errorlevel 1 pause
