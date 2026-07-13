@echo off
setlocal

REM ============================================
REM 🧠 Atlas UI - v4 launcher
REM Activa el venv si existe; si no, usa python del PATH.
REM ============================================

cd /d "%~dp0"

echo ========================================
echo   🧠 Atlas UI v4 - Iniciando...
echo   Puerto por defecto: 8401
echo ========================================
echo.

REM 1) Preferir venv local si existe
if exist ".venv\Scripts\python.exe" (
    set "PY_EXE=.venv\Scripts\python.exe"
    echo [OK] Usando venv local: %PY_EXE%
    goto :run
)

REM 2) Si no, intentar Python 3.12 / 3.11 / 3.13 via launcher py.exe
where py >nul 2>nul
if %errorlevel% == 0 (
    py -3.13 -m streamlit run atlas_ui.py --server.port 8501
    if %errorlevel% == 0 goto :end
    py -3.12 -m streamlit run atlas_ui.py --server.port 8501
    if %errorlevel% == 0 goto :end
    py -3.11 -m streamlit run atlas_ui.py --server.port 8501
    if %errorlevel% == 0 goto :end
)

REM 3) Ultimo fallback: streamlit del PATH
echo [WARN] No se encontro venv ni py.exe; usando streamlit global.
streamlit run atlas_ui.py --server.port 8501
goto :end

:run
"%PY_EXE%" -m streamlit run atlas_ui.py --server.port 8401

:end
echo.
pause
endlocal
