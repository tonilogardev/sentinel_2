FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Instalar dependencias básicas y GDAL
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    gdal-bin \
    libgdal-dev \
    python3 \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# (Espacio reservado para compilar/instalar FORCE)
# RUN ... instalar force desde fuente o ppa ...

WORKDIR /app
CMD ["/bin/bash"]
