import os
import sys
import logging
from datetime import datetime

def setup_logger(working_folder, start_date, end_date):
    """
    Configura el sistema de logs para la sesión actual.
    Crea un archivo log con la marca de tiempo y rango de fechas de la ejecución.
    """
    # Crear directorio de logs si no existe
    log_dir = os.path.join(working_folder, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Formatear el nombre del archivo de log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"Rango_{start_date}_a_{end_date}_{timestamp}.log"
    log_filepath = os.path.join(log_dir, log_filename)
    
    # Configurar el logger raíz
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Evitar duplicación de handlers si se llama múltiples veces
    if logger.handlers:
        logger.handlers.clear()
        
    # Formato de los logs
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler para escribir en archivo
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para volcar en consola (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logging.info(f"Sesión de log iniciada correctamente.")
    logging.info(f"Archivo de log creado en: {log_filepath}")
    
    return log_filepath
