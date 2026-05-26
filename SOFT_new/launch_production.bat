@echo off
echo ========================================================
echo Limpiando directorio de trabajo K:\t
echo ========================================================
rmdir /S /Q K:\t\2026-05-01_R051 2>nul
rmdir /S /Q K:\t\2026-05-01_R008 2>nul
rmdir /S /Q K:\t\2026-05-02_R051 2>nul
rmdir /S /Q K:\t\2026-05-02_R008 2>nul
rmdir /S /Q K:\t\2026-05-03_R051 2>nul
rmdir /S /Q K:\t\2026-05-03_R008 2>nul

echo ========================================================
echo Activando entorno Conda e iniciando Pipeline SOFT_new...
echo ========================================================
call C:\Users\a.lopez.g\miniconda3\Scripts\activate.bat soft_new_env
python src\s2_process\main.py
