import sys
from .config import PipelineConfig, ConfigError

def main():
    print("Iniciando Orquestador Cloud-Native (Sin Sen2Cor)")
    
    try:
        # Etapa 0: Cargar configuración y credenciales (Aislamiento seguro)
        print("-> [ETAPA 0] Validando configuración y secretos...")
        config = PipelineConfig()
        print(f"   Configuración cargada. Motor seleccionado: {config.engine.upper()}")
        print(f"   Periodo: {config.start_date} a {config.end_date} | Órbitas: {config.orbits}")
        
    except ConfigError as e:
        print(f"\n[ERROR CRÍTICO DE CONFIGURACIÓN] {e}")
        print("El pipeline ha sido detenido para proteger los recursos.")
        sys.exit(1)
        
    # Etapa 1: Ingesta COG (S3)
    print("-> [ETAPA 1] Ingesta COG desde Copernicus S3...")
    # TODO: Invocación a s3_streamer
    
    # Etapa 2: Mosaico L1C VRT
    print("-> [ETAPA 2] Unificación Espectral (Mosaico)...")
    # TODO: gdal.BuildVRT de las bandas L1C
    
    # Etapa 3: Ejecución Docker NO-DEM
    print("-> [ETAPA 3] Lanzando contenedor de corrección plana...")
    # TODO: docker_runner (NO-DEM)
    
    # Etapa 4: Ejecución Docker CON-DEM
    print("-> [ETAPA 4] Lanzando contenedor de corrección topográfica...")
    # TODO: docker_runner (WITH-DEM)
    
    # Etapa 5: Derivados
    print("-> [ETAPA 5] Generando productos derivados (SCL, NDVI, Quicklooks)...")
    # TODO: Lógica GDAL para outputs
    
    print("\nEjecución finalizada (Dry-Run).")

if __name__ == "__main__":
    main()
