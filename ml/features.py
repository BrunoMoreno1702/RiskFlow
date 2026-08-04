from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


NUMERIC_FEATURES = [
    "amount",
    "amount_log",
    "hour",
    "day",
    "month",
    "is_night",
    "is_weekend",
    "merchant_median_amount",
    "amount_vs_merchant_median",
    "is_high_amount",
]

CATEGORICAL_FEATURES = ["merchant", "category"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET_COLUMN = "is_fraud"


def _validate_columns(df: pd.DataFrame, required_columns: list[str]) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes para engenharia de atributos: {missing}")


def build_feature_frame(
    df: pd.DataFrame,
    *,
    stats: dict[str, Any] | None = None,
    training: bool = False,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = ["amount", "merchant", "category", "timestamp"]
    _validate_columns(df, required)

    features = df.copy()
    features["timestamp"] = pd.to_datetime(features["timestamp"], errors="raise")
    features = features.sort_values("timestamp").reset_index(drop=True)
    features["amount"] = features["amount"].astype(float)

    features["hour"] = features["timestamp"].dt.hour
    features["day"] = features["timestamp"].dt.day
    features["month"] = features["timestamp"].dt.month
    features["is_night"] = (features["hour"] <= 5).astype(int)
    features["is_weekend"] = (features["timestamp"].dt.dayofweek >= 5).astype(int)
    features["amount_log"] = np.log1p(features["amount"])

    if training:
        merchant_median_series = features.groupby("merchant")["amount"].median()
        merchant_median = {merchant: float(value) for merchant, value in merchant_median_series.items()}
        global_median = float(features["amount"].median())
        high_amount_threshold = float(features["amount"].quantile(0.95))
        stats_out = {
            "merchant_median_amount": merchant_median,
            "global_median_amount": global_median,
            "high_amount_threshold": high_amount_threshold,
        }
    else:
        if stats is None:
            raise ValueError("O parâmetro 'stats' é obrigatório fora do modo de treinamento.")
        stats_out = stats

    merchant_median_map = stats_out["merchant_median_amount"]
    global_median_value = float(stats_out["global_median_amount"])
    high_amount_threshold = float(stats_out["high_amount_threshold"])

    features["merchant_median_amount"] = (
        features["merchant"].map(merchant_median_map).fillna(global_median_value).astype(float)
    )
    features["amount_vs_merchant_median"] = features["amount"] / features["merchant_median_amount"].clip(lower=1.0)
    features["is_high_amount"] = (features["amount"] >= high_amount_threshold).astype(int)

    feature_frame = features[FEATURE_COLUMNS].copy()
    return feature_frame, stats_out

