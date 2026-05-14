FROM ghcr.io/osgeo/gdal:ubuntu-small-latest

RUN apt-get update -qq && apt-get install -y -qq \
    python3-pip curl unzip && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --quiet --no-cache-dir --break-system-packages -r requirements.txt

WORKDIR /workspace
COPY src/ /workspace/src
COPY scripts/ /workspace/scripts
COPY configs/ /workspace/configs

ENV GDAL_DATA="/usr/local/gdal-internal/share/gdal"
ENV PROJ_LIB="/usr/local/gdal-internal/share/proj"
ENV PYTHONPATH="/workspace/src:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3", "-m", "s2_process.main"]
