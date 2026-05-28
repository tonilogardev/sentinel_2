import os
import json
from dotenv import load_dotenv

class ConfigError(Exception):
    pass

class PipelineConfig:
    def __init__(self, config_path: str = "pipeline.json"):
        # 1. Cargar secretos (.env)
        load_dotenv()
        self.cdse_username = os.getenv("CDSE_USERNAME")
        self.cdse_password = os.getenv("CDSE_PASSWORD")
        self.s3_endpoint = os.getenv("AWS_S3_ENDPOINT")
        self.s3_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.s3_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Validar secretos de forma temprana
        self._validate_secrets()

        # 2. Cargar configuración operativa (JSON)
        if not os.path.exists(config_path):
            raise ConfigError(f"El archivo de configuración {config_path} no existe.")
            
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.start_date = data["temporal_window"]["start_date"]
        self.end_date = data["temporal_window"]["end_date"]
        self.orbits = data["spatial_config"]["orbits"]
        self.limits_utm = data["spatial_config"]["limits_utm"]
        self.input_dir = data["paths"]["input_dir"]
        self.dem_path = data["paths"]["dem_path"]
        self.output_dir = data["paths"]["output_dir"]
        self.engine = data["processing"]["selected_engine"]

    def _validate_secrets(self):
        """Valida que ninguna credencial crítica esté vacía."""
        critical_vars = {
            "CDSE_USERNAME": self.cdse_username,
            "CDSE_PASSWORD": self.cdse_password,
            "AWS_S3_ENDPOINT": self.s3_endpoint,
            "AWS_ACCESS_KEY_ID": self.s3_access_key,
            "AWS_SECRET_ACCESS_KEY": self.s3_secret_key
        }
        
        missing = [key for key, value in critical_vars.items() if not value or value.startswith("your_")]
        if missing:
            raise ConfigError(f"Faltan o no se han configurado correctamente las siguientes credenciales en el .env: {', '.join(missing)}")
