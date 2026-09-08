@echo off
echo Starting Crime Analyst React Frontend on http://localhost:5173...
cd /d "%~dp0frontend"
set PATH=C:\Program Files\nodejs;%PATH%
npm run dev

