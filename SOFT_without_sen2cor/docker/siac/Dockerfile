FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar SIAC (Normalmente vía pip)
# RUN pip install --no-cache-dir siac-s2

WORKDIR /app
CMD ["/bin/bash"]
