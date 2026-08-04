import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/transactions")


def _fetch_payload(customers=None):
    # Quando customers nao vem, a API aplica a regra padrao dela.
    params = {"customers": customers} if customers is not None else None

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()
    return response.json()


# Concentramos validacoes de contrato aqui para evitar quebra nas etapas seguintes.
def _payload_to_dataframe(payload):
    if "data" not in payload:
        raise KeyError("A resposta da API nao contem a chave 'data'.")

    dataframe = pd.DataFrame(payload["data"])

    if dataframe.empty:
        raise ValueError("A API retornou uma lista vazia de transacoes.")

    dataframe["customer_id"] = dataframe["customer_id"].astype(str)
    dataframe["transaction_id"] = dataframe["transaction_id"].astype(str)

    return dataframe


def fetch_data(customers=None):
    payload = _fetch_payload(customers=customers)
    df = _payload_to_dataframe(payload)

    return df


if __name__ == "__main__":
    df = fetch_data()

    print(df.head())
    print("\nTotal de transacoes:", len(df))
    print("Clientes unicos:", df["customer_id"].nunique())
