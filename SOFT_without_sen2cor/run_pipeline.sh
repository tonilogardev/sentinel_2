#!/bin/bash
# Script para limpiar la basura de Docker y ejecutar el pipeline desde cero

set -e

echo -e "\n=========================================="
echo -e "    🛰️  PIPELINE SENTINEL-2 CLOUD ☁️"
echo -e "==========================================\n"

echo "[1/4] 🧹 Apagando contenedores activos y borrando volúmenes temporales..."
docker compose down -v --remove-orphans

echo "[2/4] 🗑️  Limpiando imágenes antiguas, redes y caché inútil de Docker..."
# system prune -f borra todo lo que no esté siendo usado actualmente por un contenedor
docker system prune -f

echo "[3/4] 🏗️  Construyendo las imágenes de Docker..."
# Más adelante aquí añadiremos la construcción de FORCE, SIAC, etc.
docker compose build orchestrator

echo "[4/4] 🚀 Lanzando el Orquestador..."
docker compose run --rm orchestrator python -m src.s2_process_cloud.main

echo -e "\n=========================================="
echo -e "          ✅ EJECUCIÓN FINALIZADA           "
echo -e "==========================================\n"
