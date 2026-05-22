# -*- coding: utf-8 -*-
"""
Script de testeo y verificación interactivo para el pipeline SOFT_new.
Permite ejecutar el pipeline para un rango acotado de prueba y verificar el resultado.
"""

import os
import sys
import subprocess

def main():
    print("=====================================================================")
    print("           VERIFICACIÓN DE PIPELINE S2-PROCESS (SOFT_new)")
    print("=====================================================================")
    print("Este script te permite probar el nuevo pipeline en tu entorno local.")
    print("\nInstrucciones para ejecutar en tu consola Conda de Windows:")
    print("1. Abre tu terminal de Anaconda/Miniconda.")
    print("2. Activa tu entorno conda donde tengas instalado GDAL, NumPy, OpenCV, etc.")
    print("3. Sitúate en la carpeta del proyecto:")
    print("   cd f:\\Disc_F\\Orto_S2_CAT\\antonio\\open_code_project\\SOFT_new")
    print("4. Ejecuta el pipeline usando el comando:")
    print("   set PYTHONPATH=src")
    print("   python src\\s2_process\\main.py --config pipeline.json")
    print("\n---------------------------------------------------------------------")
    
    # Comprobar si tenemos el entorno listo
    print("Verificando librerías instaladas en tu entorno de ejecución actual...")
    
    libs = ['osgeo', 'cv2', 'numpy', 'requests']
    missing_libs = []
    for lib in libs:
        try:
            __import__(lib)
            print(f"  [OK] {lib} está disponible.")
        except ImportError:
            print(f"  [ERROR] {lib} NO está instalado.")
            missing_libs.append(lib)
            
    if missing_libs:
        print("\nATENCIÓN: Te faltan algunas librerías en tu entorno Conda actual.")
        print(f"Por favor, instálalas usando: conda install -c conda-forge {' '.join(missing_libs)} o vía pip.")
    else:
        print("\n¡Todo listo! Tu entorno Conda de Windows tiene las librerías necesarias.")
        
    print("\n¿Deseas lanzar una ejecución de prueba rápida con el pipeline.json actual?")
    print("Esta prueba descargará y procesará las imágenes Sentinel-2 correspondientes a las fechas y órbitas de tu pipeline.json.")
    print("Para continuar, presiona ENTER para lanzar la prueba, o escribe 'N' para salir.")
    
    # Dado que es interactivo, dejamos que el usuario decida.
    # En entornos desatendidos, salimos amigablemente.
    try:
        response = input("\n¿Ejecutar prueba? (S/N) [N]: ").strip().upper()
    except Exception:
        # En caso de no ser interactivo o dar error
        response = "N"
        
    if response == "S" or response == "SI" or response == "":
        print("\nLanzando el pipeline en segundo plano...")
        try:
            # Lanzamos main.py con PYTHONPATH configurado
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"
            
            cmd = [sys.executable, "src/s2_process/main.py", "--config", "pipeline.json"]
            print(f"Comando: {' '.join(cmd)}")
            
            # Ejecución controlada
            subprocess.run(cmd, env=env, check=True)
            print("\n¡Ejecución de prueba finalizada!")
        except Exception as e:
            print(f"\nError al ejecutar el pipeline: {e}")
    else:
        print("\nPrueba omitida. Puedes ejecutar el comando manualmente cuando desees.")

if __name__ == "__main__":
    main()
