# Crear EXE (Windows) — Básico

Objetivo: generar `download_sentinel_2.exe` desde `soft_01/app/main.py`.

Requisitos
- Windows (Anaconda/Miniconda instalado)
- Entorno `s2-process` creado con `soft_01/environment.yml`

Pasos
1) Abrir “Anaconda Prompt” (Windows) y situarte en el repo
   - `cd X:\\antonio\\trabajos\\sentinel_2\\sentinel_2`
2) Activar el entorno
   - `conda env create -f soft_01/environment.yml -n s2-process`
   - `conda activate s2-process`
3) Instalar PyInstaller (primera vez)
   - `pip install pyinstaller`
4) Construir el ejecutable
   - `pyinstaller --onefile --name download_sentinel_2 soft_01\\app\\main.py`
5) Probar
   - `dist\\download_sentinel_2.exe`

Notas
- Compila en Windows (no WSL).
- El exe queda en `dist\\`.
