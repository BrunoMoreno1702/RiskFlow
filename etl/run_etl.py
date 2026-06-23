import argparse

from ingestion.fetch_data import fetch_data
from ingestion.load_origin import load_transactions_origin
from processing.load_prod import load_transactions_prod


def run_etl(customers=100):
    print("Iniciando ETL...")

    # Etapa 1: extração de transações brutas da API.
    print("Extraindo dados da API...")
    df = fetch_data(customers=customers)

    # Etapa 2: carga incremental na origem.
    print("Carregando dados na transactions_origin...")
    load_transactions_origin(df)

    # Etapa 3: transformação e carga da camada de consumo.
    print("Tratando e carregando dados na transactions_prod...")
    load_transactions_prod()

    print("ETL finalizado com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o pipeline ETL de transações.")

    parser.add_argument(
        "--customers",
        type=int,
        default=100,
        help="Quantidade de clientes para buscar na API."
    )

    args = parser.parse_args()

    run_etl(customers=args.customers)