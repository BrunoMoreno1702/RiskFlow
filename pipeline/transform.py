"""raw -> staging: tipagem, padronizacao e deduplicacao. Funcoes puras (sem banco)."""

from __future__ import annotations

import pandas as pd

RAW_FIELDS = [
    "transaction_id",
    "customer_id",
    "amount",
    "merchant",
    "category",
    "card_network",
    "timestamp",
    "is_fraud",
]
STAGING_COLUMNS = [
    "transaction_id",
    "customer_id",
    "amount",
    "merchant",
    "category",
    "card_network",
    "event_ts",
    "event_date",
    "is_fraud",
]


class SchemaError(Exception):
    """Payload da origem sem campos obrigatorios."""


def normalize(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=STAGING_COLUMNS)

    df = pd.DataFrame(records)
    missing = [f for f in RAW_FIELDS if f not in df.columns]
    if missing:
        raise SchemaError(f"Campos ausentes no payload: {missing}")

    for col in ("transaction_id", "customer_id", "merchant", "category", "card_network"):
        df[col] = df[col].astype("string").str.strip()
    df["category"] = df["category"].str.lower()

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").round(2)
    df["event_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["event_date"] = df["event_ts"].dt.date
    df["is_fraud"] = pd.to_numeric(df["is_fraud"], errors="coerce").astype("Int64")

    # A origem pode reenviar a mesma transacao: fica a ultima versao recebida.
    df = df.drop_duplicates(subset="transaction_id", keep="last")
    return df[STAGING_COLUMNS].reset_index(drop=True)
