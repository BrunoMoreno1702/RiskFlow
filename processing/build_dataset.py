from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


def build_dataset():
    df = pd.read_csv(DATA_DIR / "transactions.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Features temporais para capturar padrão de horário/dia de transações.
    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.day
    df["month"] = df["timestamp"].dt.month

    # Encoding categórico simples para manter o pipeline atual.
    df["merchant_code"] = df["merchant"].astype("category").cat.codes
    df["category_code"] = df["category"].astype("category").cat.codes
    df["customer_code"] = df["customer_id"].astype("category").cat.codes

    features = [
        "amount",
        "hour",
        "day",
        "month",
        "merchant_code",
        "category_code",
        "customer_code"
    ]

    X = df[features]
    y = df["is_fraud"]

    X.to_csv(DATA_DIR / "X.csv", index=False)
    y.to_csv(DATA_DIR / "y.csv", index=False)

    return X, y


if __name__ == "__main__":
    X, _ = build_dataset()
    print("Dataset pronto")
    print("Shape:", X.shape)