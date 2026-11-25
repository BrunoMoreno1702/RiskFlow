"""API de inferencia online.

Para manter as features identicas as do batch, a API busca o historico recente do
cliente na staging e usa a mesma funcao `build_features` do pipeline.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ml.features import HISTORY_WINDOW, build_features
from ml.model import FraudModel, ModelNotTrainedError, load_model
from pipeline import db

state: dict[str, FraudModel] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        state["model"] = load_model()
    except ModelNotTrainedError:
        # Sobe mesmo sem modelo: /health informa o estado e /predict devolve 503.
        pass
    yield
    state.clear()


app = FastAPI(title="RiskFlow Inference API", lifespan=lifespan)


class TransactionIn(BaseModel):
    transaction_id: str | None = None
    customer_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    merchant: str = Field(min_length=1)
    category: str = Field(min_length=1)
    card_network: str = Field(min_length=1)
    timestamp: datetime


@app.get("/health")
def health() -> dict:
    model = state.get("model")
    return {"status": "ok", "model_loaded": model is not None, "model_version": model and model.version}


@app.post("/predict")
def predict(tx: TransactionIn) -> dict:
    model = state.get("model")
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo ainda nao treinado.")

    current = pd.DataFrame(
        [
            {
                "transaction_id": tx.transaction_id or str(uuid.uuid4()),
                "customer_id": tx.customer_id,
                "amount": tx.amount,
                "merchant": tx.merchant,
                "category": tx.category.lower(),
                "card_network": tx.card_network,
                "event_ts": tx.timestamp.replace(tzinfo=None),
            }
        ]
    )
    with db.connect() as conn:
        history = db.fetch_df(
            conn,
            "SELECT transaction_id, customer_id, amount, merchant, category, card_network, event_ts "
            "FROM staging.transactions WHERE customer_id = %s AND event_ts >= %s AND event_ts < %s",
            (tx.customer_id, current["event_ts"][0] - HISTORY_WINDOW, current["event_ts"][0]),
        )

    features = build_features(current, history)
    score = float(model.score(features)[0])
    return {
        "transaction_id": features["transaction_id"][0],
        "fraud_score": round(score, 6),
        "prediction": int(score >= model.threshold),
        "threshold": model.threshold,
        "model_version": model.version,
        "customer_history_30d": len(history),
    }
