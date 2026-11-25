FROM apache/airflow:3.3.2-python3.12

# Instala as dependencias do pipeline sem deixar o pip trocar a versao do Airflow.
COPY requirements-pipeline.txt /tmp/requirements-pipeline.txt
RUN pip install --no-cache-dir "apache-airflow==3.3.2" -r /tmp/requirements-pipeline.txt
