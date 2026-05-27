@echo off
echo Activando entorno Conda...
call C:\Users\a.lopez.g\miniconda3\Scripts\activate.bat sentinel2
if %errorlevel% neq 0 (
    echo Fallo al activar Miniconda desde la ruta por defecto. Intentando 'conda activate'...
    call conda activate sentinel2
)

echo.
echo Iniciando S2-PROCESS Pipeline Automático...
echo.

set PYTHONPATH=src;%PYTHONPATH%
python src\s2_process\main.py

echo.
echo Proceso finalizado.
pause
