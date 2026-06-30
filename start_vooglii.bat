@echo off
chcp 65001 >nul

title VOOGLII Platform Launcher

echo ========================================
echo        VOOGLII Platform Launcher
echo ========================================
echo.

set PROJECT_DIR=C:\Users\Andrey\Desktop\WildberriesAgent
set FRONTEND_DIR=%PROJECT_DIR%\frontend

echo Starting VOOGLII Backend API...
start "VOOGLII Backend API" cmd /k "cd /d %PROJECT_DIR% && python api_server.py"

timeout /t 5 /nobreak >nul

echo Starting VOOGLII Frontend...
start "VOOGLII Frontend" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

timeout /t 8 /nobreak >nul

echo Opening browser...
start http://localhost:3000

echo.
echo VOOGLII started.
echo Backend:  http://127.0.0.1:8000/api/health
echo Frontend: http://localhost:3000
echo.
echo Do not close backend/frontend windows while using VOOGLII.
pause
