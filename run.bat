@echo off
title okDRIVER

echo Starting Backend API (http://localhost:8000)...
start "okDRIVER Backend" cmd /k "cd /d "%~dp0backend" && python run_server.py"

echo Starting Frontend Web (http://localhost:3000)...
start "okDRIVER Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ===================================================
echo  okDRIVER Backend and Frontend are now running!
echo  - Backend:  http://localhost:8000
echo  - Frontend: http://localhost:3000
echo ===================================================
