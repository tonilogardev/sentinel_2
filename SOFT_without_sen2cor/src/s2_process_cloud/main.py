import sys
import os
from datetime import datetime, timedelta
from src.s2_process_cloud.config import PipelineConfig, ConfigError
from src.s2_process_cloud.utils.logger import setup_logger
from src.s2_process_cloud.utils.console_ui import PipelineConsoleUI
from src.s2_process_cloud.download.s3_streamer import CDSEDownloader

def get_date_list(start_str: str, end_str: str):
    """Genera una lista de fechas (str) entre start y end."""
    start_dt = datetime.strptime(start_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_str, "%Y-%m-%d")
    dates = []
    current_dt = start_dt
    while current_dt <= end_dt:
        dates.append(current_dt.strftime("%Y-%m-%d"))
        current_dt += timedelta(days=1)
    return dates

def main():
    ui = PipelineConsoleUI()
    ui.display_header("INICIANDO ORQUESTADOR CLOUD-NATIVE")
    
    try:
        # Etapa 0: Configuración y Logs
        config = PipelineConfig()
        log_file = setup_logger(config.working_folder, config.date_range_start, config.date_range_end)
        ui.print_success(f"Configuración cargada. Engine: {config.selected_engine.upper()}")
        
        dates = get_date_list(config.date_range_start, config.date_range_end)
        ui.print_success(f"Días a procesar: {len(dates)} | Órbitas: {config.orbits}")
        
    except ConfigError as e:
        ui.print_error(f"Error de configuración: {e}")
        sys.exit(1)
        
    downloader = CDSEDownloader(config)
    ui.start_pipeline(total_stages=5)
    
    try:
        for date_str in dates:
            for orbit in config.orbits:
                ui.display_header(f"Órbita {orbit} | Fecha {date_str}")
                
                # Etapa 1: Ingesta de Datos (OData Search & Download)
                ui.update_stage(f"1. Ingesta L1C desde Copernicus CDSE para {orbit}...", stage_num=1)
                
                products = downloader.search_products(orbit, date_str, config.poly_search)
                if not products:
                    ui.print_error(f"No hay gránulos disponibles para {orbit} en {date_str}. Saltando...")
                    continue
                
                ui.print_success(f"Encontrados {len(products)} gránulos (últimas baselines). Iniciando descarga...")
                
                # Crear la carpeta de destino: ./data/R051/2026-05-01/crudo
                target_dir = os.path.join(config.working_folder, orbit, date_str, "crudo")
                
                for p in products:
                    prod_id = p.get('Id')
                    prod_name = p.get('Name')
                    ui.print_success(f"Descargando {prod_name}...")
                    downloader.download_product_zip(prod_id, prod_name, target_dir)
                    
                ui.print_success(f"Todas las descargas de {orbit} finalizadas correctamente.")
                
                # Mock del resto del pipeline por ahora
                ui.update_stage("2. Unificación Espectral y Mosaico (GDAL)...", stage_num=2)
                ui.update_stage(f"3. Ejecución de Motor Atmosférico ({config.selected_engine.upper()})...", stage_num=3)
                ui.update_stage("4. Generación de Productos Derivados (SCL, NDVI)...", stage_num=4)
                ui.update_stage("5. Segmento Finalizado y Limpieza.", stage_num=5)

    except Exception as e:
        ui.print_error(f"Error crítico en la ejecución del pipeline: {e}")
    finally:
        ui.stop_pipeline()
        print("\nEjecución finalizada.")

if __name__ == "__main__":
    main()
