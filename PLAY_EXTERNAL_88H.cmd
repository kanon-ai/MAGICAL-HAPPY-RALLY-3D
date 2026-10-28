@echo off
cd /d "%~dp0"
python tools\play.py --external-88h %*
if errorlevel 1 pause
