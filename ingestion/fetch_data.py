import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/transactions")

def fetch_data(customers=100):
    response = requests.get(
        API_URL,
        params={"customers": customers},
        timeout=30
    )

    response.raise_for_status()
    payload = response.json()

    if "data" not in payload:
        raise KeyError("A resposta da API não contém a chave 'data'.")

    df = pd.DataFrame(payload["data"])

    if df.empty:
        raise ValueError("A API retornou uma lista vazia de transações.")

    df["customer_id"] = df["customer_id"].astype(str)
    df["transaction_id"] = df["transaction_id"].astype(str)

    return df

if __name__ == "__main__":
    df = fetch_data(customers=100)

    print(df.head())
    print("\nTotal de transações:", len(df))
    print("Clientes únicos:", df["customer_id"].nunique())