import subprocess
import os

class DockerRunner:
    def __init__(self, engine: str, compose_file: str = "docker-compose.yml"):
        """
        :param engine: 'force', 'siac', o 'acolite'
        """
        self.engine = engine.lower()
        self.compose_file = compose_file

    def run_correction(self, input_path: str, mode: str = "NO-DEM"):
        """
        Invoca docker-compose run para el contenedor seleccionado.
        :param mode: 'NO-DEM' o 'WITH-DEM'
        """
        print(f"      [DOCKER] Iniciando contenedor: {self.engine} en modo {mode}")
        
        # En una implementación real, se ejecutaría algo como esto:
        # cmd = ["docker-compose", "-f", self.compose_file, "run", "--rm", 
        #        "-e", f"PROCESS_MODE={mode}", self.engine]
        # 
        # try:
        #     subprocess.run(cmd, check=True)
        # except subprocess.CalledProcessError as e:
        #     print(f"Error ejecutando Docker: {e}")
        
        print(f"      [DOCKER] El motor {self.engine.upper()} ha finalizado la corrección {mode}.")
        
        # Simula devolver la ruta donde el contenedor depositó los resultados
        return f"./output/{self.engine}/{mode}/"
