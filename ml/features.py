"""Engenharia de atributos compartilhada entre pipeline batch, treino e inferencia online.

Todas as features sao point-in-time: para cada transacao, usam apenas transacoes do
mesmo cliente que aconteceram estritamente antes dela. Isso evita vazamento de
informacao do futuro e garante que treino e producao calculem exatamente o mesmo valor.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ID_COLUMNS = ["transaction_id", "customer_id", "event_ts", "event_date", "merchant"]
NUMERIC_FEATURES = [
    "amount",
    "amount_log",
    "hour",
    "is_night",
    "is_weekend",
    "cust_tx_count_1h",
    "cust_tx_count_24h",
    "cust_tx_count_30d",
    "cust_avg_amount_30d",
    "amount_vs_cust_avg",
    "is_new_category_for_customer",
]
CATEGORICAL_FEATURES = ["category", "card_network"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "is_fraud"

# Quanto historico por cliente as features precisam olhar para tras.
HISTORY_WINDOW = pd.Timedelta(days=30)

_REQUIRED = ["transaction_id", "customer_id", "amount", "category", "card_network", "event_ts"]


def _rolling_prior(frame: pd.DataFrame, keys: list[str], window: str, how: str) -> np.ndarray:
    """Agregado de `amount` na janela [t - window, t), por grupo, alinhado a `frame`."""
    ordered = frame.sort_values([*keys, "event_ts", "transaction_id"])
    rolled = (
        ordered.set_index("event_ts")
        .groupby(keys, sort=False)["amount"]
        .rolling(window, closed="left")
        .agg(how)
    )
    return pd.Series(rolled.to_numpy(), index=ordered.index).reindex(frame.index).to_numpy()


def build_features(current: pd.DataFrame, history: pd.DataFrame | None = None) -> pd.DataFrame:
    """Calcula features para as linhas de `current`.

    `history` sao transacoes anteriores (ex.: ultimos 30 dias) usadas so como contexto.
    Retorna uma linha por transacao de `current`, com colunas ID + features (+ alvo, se existir).
    """
    missing = [c for c in _REQUIRED if c not in current.columns]
    if missing:
        raise ValueError(f"Colunas ausentes para engenharia de atributos: {missing}")

    cur = current.copy()
    cur["_is_current"] = True
    frames = [cur]
    if history is not None and not history.empty:
        hist = history[~history["transaction_id"].isin(cur["transaction_id"])].copy()
        hist["_is_current"] = False
        frames.append(hist)

    df = pd.concat(frames, ignore_index=True)
    df["event_ts"] = pd.to_datetime(df["event_ts"])
    df["amount"] = df["amount"].astype(float)

    df["cust_tx_count_1h"] = _rolling_prior(df, ["customer_id"], "1h", "count")
    df["cust_tx_count_24h"] = _rolling_prior(df, ["customer_id"], "24h", "count")
    df["cust_tx_count_30d"] = _rolling_prior(df, ["customer_id"], "30D", "count")
    df["cust_avg_amount_30d"] = _rolling_prior(df, ["customer_id"], "30D", "mean")
    same_category_30d = _rolling_prior(df, ["customer_id", "category"], "30D", "count")

    out = df[df["_is_current"]].copy()
    first_seen = np.isnan(out["cust_avg_amount_30d"].to_numpy(dtype=float))
    # Cliente sem historico: media = propria transacao (razao 1) e categoria nao e "nova".
    out["cust_avg_amount_30d"] = out["cust_avg_amount_30d"].fillna(out["amount"])
    out["is_new_category_for_customer"] = (
        (np.nan_to_num(same_category_30d[out.index]) == 0) & ~first_seen
    ).astype(int)

    for col in ("cust_tx_count_1h", "cust_tx_count_24h", "cust_tx_count_30d"):
        out[col] = out[col].fillna(0).astype(int)

    out["amount_log"] = np.log1p(out["amount"])
    out["amount_vs_cust_avg"] = out["amount"] / out["cust_avg_amount_30d"].clip(lower=1.0)
    out["hour"] = out["event_ts"].dt.hour
    out["is_night"] = (out["hour"] <= 5).astype(int)
    out["is_weekend"] = (out["event_ts"].dt.dayofweek >= 5).astype(int)
    out["event_date"] = out["event_ts"].dt.date
    if "merchant" not in out.columns:
        out["merchant"] = ""

    columns = ID_COLUMNS + FEATURE_COLUMNS
    if TARGET_COLUMN in out.columns:
        out[TARGET_COLUMN] = out[TARGET_COLUMN].astype(int)
        columns.append(TARGET_COLUMN)

    return out.sort_values(["event_ts", "transaction_id"])[columns].reset_index(drop=True)
