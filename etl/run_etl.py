import argparse

from ingestion.fetch_data import fetch_data
from ingestion.load_origin import load_transactions_origin
from processing.load_prod import load_transactions_prod


# Orquestra um ciclo completo: extrair, carregar origem e publicar camada de consumo.
def run_etl(customers=None):
    print("Iniciando ETL...")

    print("Extraindo dados da API...")
    df = fetch_data(customers=customers)

    print("Carregando dados na transactions_origin...")
    inserted_transaction_ids = load_transactions_origin(df)

    print("Tratando e carregando dados na transactions_prod...")
    load_transactions_prod(transaction_ids=inserted_transaction_ids)

    print("ETL finalizado com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o pipeline ETL de transacoes.")

    parser.add_argument(
        "--customers",
        type=int,
        default=None,
        help="Quantidade de clientes para buscar na API. Quando omitido, usa o padrao da API."
    )

    args = parser.parse_args()

    run_etl(customers=args.customers)
