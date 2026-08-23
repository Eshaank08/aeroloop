@echo off
cd /d "%~dp0"
echo Starting local server and opening the 3D engine model...
start "" http://localhost:8743/nacelle_3d.html
python -m http.server 8743
