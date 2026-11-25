-- Executado uma unica vez, na criacao do volume do Postgres.
-- Banco separado para os metadados do Airflow: o banco do projeto fica limpo.
CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;
