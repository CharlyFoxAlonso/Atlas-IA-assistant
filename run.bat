@echo off
setlocal

REM ============================================
REM 🧠 Atlas CLI - v4 launcher
REM Ejecuta run.py -> atlas_chat.py (terminal interactiva)
REM ============================================

cd /d "%~dp0"

echo ========================================
echo   🧠 Atlas CLI v4 - Terminal interactiva
echo ========================================
echo.

REM 1) Preferir venv local si existe
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
    echo [OK] Usando venv local: %PY_EXE%
    goto :run
)

REM 2) Fallback: py.exe con 3.13 / 3.12 / 3.11
where py >nul 2>nul
if %errorlevel% == 0 (
    py -3.13 run.py
    if %errorlevel% == 0 goto :end
    py -3.12 run.py
    if %errorlevel% == 0 goto :end
    py -3.11 run.py
    if %errorlevel% == 0 goto :end
)

REM 3) Ultimo fallback: python del PATH
echo [WARN] No se encontro venv ni py.exe; usando python global.
python run.py
goto :end

:run
"%PY_EXE%" run.py

:end
echo.
endlocal
