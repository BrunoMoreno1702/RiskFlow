# Imagem das aplicacoes Python (Source API, Inference API, CLI do pipeline).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY source_api ./source_api
COPY pipeline ./pipeline
COPY ml ./ml
COPY sql ./sql
COPY dashboard ./dashboard
COPY .streamlit ./.streamlit

# Mesmo UID/GID do usuario da imagem oficial do Airflow (50000:0): os dois
# containers escrevem e leem o volume compartilhado de artefatos do modelo.
RUN useradd --create-home --uid 50000 --gid 0 riskflow && mkdir -p /artifacts && chown 50000:0 /artifacts
USER riskflow
