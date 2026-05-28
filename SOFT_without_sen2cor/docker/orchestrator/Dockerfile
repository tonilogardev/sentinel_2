FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del orquestador
RUN pip install --no-cache-dir \
    requests \
    boto3 \
    python-dotenv \
    rich

# Mantener el contenedor vivo para poder entrar e interactuar
CMD ["tail", "-f", "/dev/null"]
