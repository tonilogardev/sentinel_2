import os
import json
import logging
from dotenv import load_dotenv

class ConfigError(Exception):
    pass

class PipelineConfig:
    def __init__(self, json_path: str = "pipeline.json"):
        self.json_path = json_path
        self.params = {}
        
        # 1. Cargar secretos (.env)
        # load_dotenv es util para testeo local en WSL. En Docker, compose los inyecta.
        load_dotenv()
        self.cdse_username = os.getenv("CDSE_USERNAME")
        self.cdse_password = os.getenv("CDSE_PASSWORD")
        self.s3_endpoint = os.getenv("AWS_S3_ENDPOINT")
        self.s3_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.s3_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        self._validate_secrets()
        self._load_json()

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

    def _load_json(self):
        """Carga los parámetros del archivo JSON."""
        if not os.path.exists(self.json_path):
            raise ConfigError(f"El archivo de configuración {self.json_path} no existe.")
            
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.params = json.load(f)
        except Exception as e:
            raise ConfigError(f"Error al abrir o decodificar {self.json_path}: {e}")

    def _resolve_path(self, p):
        """Resuelve paths relativos convirtiéndolos a absolutos según la ubicación del JSON."""
        if not p or p.startswith("/"):
            return p
        # En Docker, los volumenes suelen montarse en raiz (/data, /output), 
        # pero si empieza por ./ respetamos la resolucion relativa
        return os.path.normpath(os.path.join(os.path.dirname(self.json_path), p))

    # --- Propiedades de API ---
    @property
    def api_download_url(self):
        return self.params.get("api", {}).get("downloadURL")

    @property
    def api_auth_url(self):
        return self.params.get("api", {}).get("authentificationURL")

    # --- Propiedades de Tiempo ---
    @property
    def date_range_start(self):
        return self.params.get("dateRange", {}).get("start")

    @property
    def date_range_end(self):
        return self.params.get("dateRange", {}).get("end")

    # --- Propiedades de Espacio (Área/Órbitas) ---
    @property
    def orbits(self):
        return self.params.get("orbits", [])

    @property
    def limits_utm(self):
        return self.params.get("area", {}).get("limitsUTM", {})

    @property
    def granules_per_orbit(self):
        return self.params.get("area", {}).get("granulesPerOrbit", {})
        
    @property
    def poly_search(self):
        return self.params.get("area", {}).get("polySearch")

    # --- Propiedades de Workspace ---
    @property
    def working_folder(self):
        return self._resolve_path(self.params.get("workspace", {}).get("workingFolder", "./data"))
        
    @property
    def output_folder(self):
        return self._resolve_path(self.params.get("workspace", {}).get("outputFolder", "./output"))

    # --- Propiedades de Procesamiento ---
    @property
    def target_resolution(self):
        return self.params.get("processing", {}).get("targetResolution", 10)
        
    @property
    def selected_engine(self):
        return self.params.get("processing", {}).get("selectedEngine", "force")
