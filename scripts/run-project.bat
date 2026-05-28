@echo off
title AI Career Assistant - Full Stack Runner

echo ===============================
echo Starting Backend + Frontend...
echo ===============================

:: Go to project root
cd /d %~dp0

:: -------------------------------
:: Start Backend (FastAPI)
:: -------------------------------
echo Starting Backend...
start cmd /k "cd server && call ..\venv\Scripts\activate && py -m uvicorn main:app --reload"

:: wait a bit so backend starts first
timeout /t 3 > nul

:: -------------------------------
:: Start Frontend (Vite)
:: -------------------------------
echo Starting Frontend...
start cmd /k "cd client && npm run dev"

echo ===============================
echo Both servers are starting...
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
echo ===============================

pause