FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Clonar ACOLITE (es un repositorio de GitHub)
# RUN git clone https://github.com/acolite/acolite.git /opt/acolite
# RUN pip install -r /opt/acolite/requirements.txt

WORKDIR /app
CMD ["/bin/bash"]
