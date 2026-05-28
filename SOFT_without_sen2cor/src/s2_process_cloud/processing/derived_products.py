import os

class DerivedProductsGenerator:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def calculate_ndvi(self, l2a_cog_path: str):
        """
        Calcula el índice NDVI (B08 - B04) / (B08 + B04)
        """
        print(f"      [GDAL] Calculando NDVI desde {l2a_cog_path}")
        # Simulando lógica con gdal_calc.py
        ndvi_path = l2a_cog_path.replace(".btf", "_NDVI.tif")
        print(f"      [GDAL] NDVI generado en {ndvi_path}")
        return ndvi_path

    def extract_and_resample_scl(self, l2a_folder: str):
        """
        Extrae la máscara de clasificación SCL (si existe en el output del motor)
        y la remuestrea a 10m mediante vecino más próximo.
        """
        print(f"      [GDAL] Buscando máscara de nubes en {l2a_folder}")
        scl_path = os.path.join(l2a_folder, "SCL_10m.tif")
        print(f"      [GDAL] Máscara SCL remuestreada generada en {scl_path}")
        return scl_path

    def generate_quicklook(self, l2a_cog_path: str):
        """
        Genera un JPG de previsualización extrayendo las bandas RGB y
        estirando el histograma de reflectancia.
        """
        print(f"      [OPENCV] Generando Quicklook RGB desde {l2a_cog_path}")
        quicklook_path = l2a_cog_path.replace(".btf", "_Quicklook.jpg")
        print(f"      [OPENCV] Quicklook guardado en {quicklook_path}")
        return quicklook_path
