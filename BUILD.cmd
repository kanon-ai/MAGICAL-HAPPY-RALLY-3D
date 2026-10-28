@echo off
cd /d "%~dp0"
python tools\build.py --pack-only
if errorlevel 1 pause
