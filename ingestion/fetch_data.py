import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/transactions")


def _fetch_payload(customers):
    response = requests.get(
        API_URL,
        params={"customers": customers},
        timeout=30
    )

    response.raise_for_status()
    return response.json()


def _payload_to_dataframe(payload):
    # A chave "data" é o contrato da API para o pipeline de ingestão.
    if "data" not in payload:
        raise KeyError("A resposta da API não contém a chave 'data'.")

    dataframe = pd.DataFrame(payload["data"])

    if dataframe.empty:
        raise ValueError("A API retornou uma lista vazia de transações.")

    dataframe["customer_id"] = dataframe["customer_id"].astype(str)
    dataframe["transaction_id"] = dataframe["transaction_id"].astype(str)

    return dataframe


def fetch_data(customers=100):
    payload = _fetch_payload(customers=customers)
    df = _payload_to_dataframe(payload)

    return df


if __name__ == "__main__":
    df = fetch_data(customers=100)

    print(df.head())
    print("\nTotal de transações:", len(df))
    print("Clientes únicos:", df["customer_id"].nunique())