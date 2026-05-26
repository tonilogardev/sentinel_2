import os
import json
import logging

class PipelineConfig:
    def __init__(self, json_path, env_path=None):
        self.json_path = json_path
        self.env_path = env_path or os.path.join(os.path.dirname(json_path), ".env")
        self.params = {}
        self.env_vars = {}
        
        self._load_json()
        self._load_env()
        
    def _load_json(self):
        """Carga los parámetros del archivo JSON."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.params = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Error al abrir o decodificar {self.json_path}: {e}")
            
    def _load_env(self):
        """Carga las credenciales del archivo .env sin dependencias externas."""
        if not os.path.isfile(self.env_path):
            logging.warning(f"No se encontró archivo de variables de entorno en: {self.env_path}. Se usarán variables del sistema.")
            return
            
        try:
            with open(self.env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, val = line.split('=', 1)
                        self.env_vars[key.strip()] = val.strip()
                        os.environ[key.strip()] = val.strip()
        except Exception as e:
            logging.error(f"Error al leer el archivo .env: {e}")

    def _resolve_path(self, p):
        """Resuelve paths relativos convirtiéndolos a absolutos según la ubicación del JSON."""
        if not p or "/workspace/" in p:
            return p
        if not os.path.isabs(p):
            return os.path.normpath(os.path.join(os.path.dirname(self.json_path), p))
        return p

    @property
    def api_download_url(self):
        return self.params.get("api", {}).get("downloadURL")

    @property
    def api_auth_url(self):
        return self.params.get("api", {}).get("authentificationURL")

    @property
    def date_range_start(self):
        return self.params.get("dateRange", {}).get("start")

    @property
    def date_range_end(self):
        return self.params.get("dateRange", {}).get("end")

    @property
    def orbits(self):
        return self.params.get("orbits", [])

    @property
    def working_folder(self):
        return self._resolve_path(self.params.get("workspace", {}).get("workingFolder"))

    @property
    def quicklook_dir(self):
        return self._resolve_path(self.params.get("workspace", {}).get("quicklookDir"))

    @property
    def sen2cor_bin(self):
        return self._resolve_path(self.params.get("workspace", {}).get("sen2cor", {}).get("bin"))

    @property
    def l2a_gipp_demcat(self):
        return self._resolve_path(self.params.get("workspace", {}).get("sen2cor", {}).get("gippPath"))

    @property
    def poly_search(self):
        return self.params.get("area", {}).get("polySearch")

    @property
    def granules_per_orbit(self):
        return self.params.get("area", {}).get("granulesPerOrbit", {})

    @property
    def limits_utm(self):
        return self.params.get("area", {}).get("limitsUTM", {})

    @property
    def per_orbit_zone_utm(self):
        return self.params.get("area", {}).get("perOrbitZoneUTM", {})

    @property
    def check_two_datastrips(self):
        return self.params.get("pipeline", {}).get("checkTwoDatastrips") == "YES"

    @property
    def allowed_inner_zeros_l2a(self):
        return self.params.get("pipeline", {}).get("AllowedInnerzerosproductL2A") == "YES"

    @property
    def product_l1c_generation(self):
        return self.params.get("pipeline", {}).get("productL1Cgeneration") == "YES"

    @property
    def only_last_baseline(self):
        return self.params.get("pipeline", {}).get("onlyLastBaselineForGranule") == "YES"

    def get_credential(self, name):
        """Retorna credenciales cargadas de .env o del sistema."""
        return os.getenv(name, self.env_vars.get(name))
