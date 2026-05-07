@echo off
setlocal
set ROOT=%~dp0
"%ROOT%\.venv\Scripts\python.exe" -m helix_desktop.desktop_launcher
