@echo off
echo ====================================
echo Biblioteca de Jurisprudencia
echo ====================================
echo.

echo [1/4] Iniciando Docker (PostgreSQL y MinIO)...
docker-compose up -d
if %errorlevel% neq 0 (
    echo Error al iniciar Docker
    pause
    exit /b 1
)
echo ✓ Docker iniciado
echo.

echo [2/4] Esperando a que los servicios estén listos...
timeout /t 5 /nobreak >nul
echo ✓ Servicios listos
echo.

echo [3/4] Iniciando Backend (FastAPI)...
start "Backend - FastAPI" cmd /k "cd backend && venv\Scripts\activate && python -m app.main"
echo ✓ Backend iniciado en http://localhost:8000
echo.

echo [4/4] Iniciando Frontend (Next.js)...
timeout /t 3 /nobreak >nul
start "Frontend - Next.js" cmd /k "cd frontend && npm run dev"
echo ✓ Frontend iniciado en http://localhost:3000
echo.

echo ====================================
echo ✅ Aplicación iniciada correctamente
echo ====================================
echo.
echo Frontend: http://localhost:3000
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo MinIO Console: http://localhost:9001
echo.
echo Presiona cualquier tecla para salir...
pause >nul
