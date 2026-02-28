@echo off
REM Start all Antigravity services for Windows

echo ==========================================
echo ANTIGRAVITY - Starting All Services
echo ==========================================
echo.

echo This will open 3 terminal windows for:
echo   1. Agent Service (Port 8002)
echo   2. Orchestrator Service (Port 8003)  
echo   3. Runtime Service (Port 8001)
echo.

cd %~dp0

REM Start Agent Service
start "Agent Service (8002)" cmd /k "cd services\agent && python main.py"

REM Wait 2 seconds
timeout /t 2 /nobreak >nul

REM Start Orchestrator Service
start "Orchestrator Service (8003)" cmd /k "cd services\orchestrator && python main.py"

REM Wait 2 seconds
timeout /t 2 /nobreak >nul

REM Start Runtime Service
start "Runtime Service (8001)" cmd /k "cd services\runtime && python main.py"

echo.
echo ==========================================
echo All services started!
echo ==========================================
echo.
echo Services running at:
echo   - Runtime: http://localhost:8001
echo   - Agent: http://localhost:8002
echo   - Orchestrator: http://localhost:8003
echo.
echo Test the system:
echo   cd tests
echo   bash test_live_wiring.sh
echo.
pause
