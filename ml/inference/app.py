from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from ml.features import FEATURE_COLUMNS, build_feature_frame


MODEL_PATH = Path(os.getenv("MODEL_PATH", "ml/artifacts/model.joblib"))
FEATURE_STATS_PATH = Path(os.getenv("FEATURE_STATS_PATH", "ml/artifacts/feature_stats.json"))
METADATA_PATH = Path(os.getenv("METADATA_PATH", "ml/artifacts/metadata.json"))

app = FastAPI(title="Fraud Model Inference API")

MODEL: Any = None
FEATURE_STATS: dict[str, Any] | None = None
METADATA: dict[str, Any] | None = None


class TransactionInput(BaseModel):
    transaction_id: str | None = Field(default=None, description="Identificador transacao (opcional).")
    customer_id: str = Field(description="Identificador do cliente.")
    amount: float = Field(gt=0, description="Valor da transacao.")
    merchant: str = Field(min_length=1, description="Estabelecimento.")
    category: str = Field(min_length=1, description="Categoria da compra.")
    timestamp: datetime = Field(description="Data e hora da transacao em formato ISO-8601.")


@app.on_event("startup")
def load_artifacts() -> None:
    global MODEL, FEATURE_STATS, METADATA

    if not MODEL_PATH.exists():
        raise RuntimeError(f"Arquivo de modelo nao encontrado: {MODEL_PATH}")
    if not FEATURE_STATS_PATH.exists():
        raise RuntimeError(f"Arquivo de estatisticas de features nao encontrado: {FEATURE_STATS_PATH}")
    if not METADATA_PATH.exists():
        raise RuntimeError(f"Arquivo de metadata nao encontrado: {METADATA_PATH}")

    MODEL = joblib.load(MODEL_PATH)

    with FEATURE_STATS_PATH.open("r", encoding="utf-8") as file:
        FEATURE_STATS = json.load(file)

    with METADATA_PATH.open("r", encoding="utf-8") as file:
        METADATA = json.load(file)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict")
def predict(payload: TransactionInput) -> dict[str, Any]:
    if MODEL is None or FEATURE_STATS is None or METADATA is None:
        raise RuntimeError("Artefatos ainda nao foram carregados.")

    row = {
        "transaction_id": payload.transaction_id,
        "customer_id": payload.customer_id,
        "amount": payload.amount,
        "merchant": payload.merchant,
        "category": payload.category,
        "timestamp": payload.timestamp.isoformat(),
    }
    raw_df = pd.DataFrame([row])

    feature_frame, _ = build_feature_frame(raw_df, stats=FEATURE_STATS, training=False)
    score = float(MODEL.predict_proba(feature_frame[FEATURE_COLUMNS])[:, 1][0])

    threshold = float(METADATA.get("threshold", 0.5))
    prediction = int(score >= threshold)

    return {
        "fraud_score": score,
        "prediction": prediction,
        "threshold": threshold,
        "model_name": METADATA.get("model_name"),
    }

