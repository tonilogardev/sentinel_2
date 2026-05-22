# 💡 Tips y Comandos Útiles

Este documento sirve como repositorio rápido de comandos de terminal, utilidades de mantenimiento y atajos para gestionar el pipeline.

## 1. Mantenimiento del Entorno Conda (`environment.yml`)

Cuando modificamos el archivo `environment.yml` (por ejemplo, para añadir nuevas librerías como `rich`), existen dos formas de trasladar esos cambios al entorno activo.

### Opción A: Actualización rápida (Recomendada)
Actualiza el entorno inyectando lo nuevo y borrando (`--prune`) lo que se haya eliminado del fichero maestro:
```bash
conda deactivate
conda env update -n soft_new_env -f environment.yml --prune
conda activate soft_new_env
```

### Opción B: Instalación limpia ("Vía Nuclear")
Borra por completo el entorno y lo vuelve a generar desde cero. Ideal cuando hay conflictos extraños de dependencias:
```bash
conda deactivate
conda env remove -n soft_new_env
conda env create -f environment.yml
conda activate soft_new_env
```
