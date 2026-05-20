@echo off
setlocal

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo Starting backend...
start "Backend" cmd /k "cd /d "%ROOT%\backend" && "%ROOT%\venv\Scripts\python.exe" -m uvicorn main:app --reload --port 8000"

echo Starting frontend...
start "Frontend" cmd /k "cd /d "%ROOT%\frontend" && npm install --silent && npm run dev"

echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Both are running in their own windows.
echo Close those windows (or press Ctrl+C in them) to stop each service.
echo.
pause
endlocal