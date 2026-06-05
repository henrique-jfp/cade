@echo off
title Cade - Instant Media Search
echo ========================================
echo   Iniciando Cade (Backend + Frontend)
echo ========================================

:: Inicia o Backend em uma nova janela
start "Cade - Backend" cmd /k "cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

:: Inicia o Frontend em uma nova janela
start "Cade - Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo [OK] Backend rodando em: http://localhost:8000
echo [OK] Frontend rodando em: http://localhost:5173
echo.
echo Aproveite!
pause
