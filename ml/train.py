"""Treino do modelo de fraude a partir do mart.

- Split temporal por dia (treino 70% / validacao 15% / teste 15% dos dias), nunca aleatorio:
  o modelo e avaliado em dias que ele nao viu e que vem depois do treino.
- Selecao por PR-AUC na validacao (classes muito desbalanceadas: ~1% de fraude).
- Threshold escolhido na validacao, metricas finais reportadas no teste.
- Uma regra simples (valor acima do p95) e reportada como baseline: o modelo so se
  justifica se for claramente melhor que ela.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, precision_recall_curve, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES, TARGET_COLUMN
from ml.model import METADATA_FILE, MODEL_FILE

log = logging.getLogger(__name__)
MIN_POSITIVES_PER_SPLIT = 5


def temporal_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    days = np.sort(df["event_date"].unique())
    if len(days) < 10:
        raise ValueError(f"Sao necessarios pelo menos 10 dias de dados; ha {len(days)}.")
    train_end, val_end = days[int(len(days) * 0.70)], days[int(len(days) * 0.85)]
    return (
        df[df["event_date"] < train_end],
        df[(df["event_date"] >= train_end) & (df["event_date"] < val_end)],
        df[df["event_date"] >= val_end],
    )


def _candidates(random_state: int) -> dict[str, Pipeline]:
    def pre() -> ColumnTransformer:
        return ColumnTransformer(
            [
                ("num", StandardScaler(), NUMERIC_FEATURES),
                ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ]
        )

    return {
        "logistic_regression": Pipeline(
            [("pre", pre()), ("model", LogisticRegression(max_iter=2000, class_weight="balanced"))]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("pre", pre()),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        max_iter=300, learning_rate=0.05, class_weight="balanced", random_state=random_state
                    ),
                ),
            ]
        ),
    }


def _best_f1_threshold(y: pd.Series, scores: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y, scores)
    f1 = 2 * precision[:-1] * recall[:-1] / (precision[:-1] + recall[:-1] + 1e-12)
    return float(thresholds[int(np.argmax(f1))]) if len(thresholds) else 0.5


def _metrics(y: pd.Series, scores: np.ndarray, threshold: float) -> dict[str, float]:
    pred = (scores >= threshold).astype(int)
    return {
        "pr_auc": round(float(average_precision_score(y, scores)), 4),
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "positives": int(y.sum()),
        "rows": len(y),
    }


def train_from_frame(df: pd.DataFrame, artifacts_dir: Path, random_state: int = 42) -> dict:
    train, val, test = temporal_split(df)
    for name, part in (("treino", train), ("validacao", val), ("teste", test)):
        if part[TARGET_COLUMN].sum() < MIN_POSITIVES_PER_SPLIT:
            raise ValueError(f"Poucas fraudes no conjunto de {name}; aumente o periodo de dados.")

    x_train, y_train = train[FEATURE_COLUMNS], train[TARGET_COLUMN]
    x_val, y_val = val[FEATURE_COLUMNS], val[TARGET_COLUMN]
    x_test, y_test = test[FEATURE_COLUMNS], test[TARGET_COLUMN]

    comparison, best = {}, None
    for name, pipeline in _candidates(random_state).items():
        pipeline.fit(x_train, y_train)
        val_scores = pipeline.predict_proba(x_val)[:, 1]
        pr_auc = float(average_precision_score(y_val, val_scores))
        comparison[name] = round(pr_auc, 4)
        log.info("%s: PR-AUC validacao = %.4f", name, pr_auc)
        if best is None or pr_auc > best[1]:
            best = (name, pr_auc, pipeline, _best_f1_threshold(y_val, val_scores))

    name, _, pipeline, threshold = best
    test_scores = pipeline.predict_proba(x_test)[:, 1]

    # Baseline: regra "valor acima do p95 do treino" usando o proprio valor como score.
    p95 = float(train["amount"].quantile(0.95))
    baseline = _metrics(y_test, test["amount"].to_numpy(), p95)

    version = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    metadata = {
        "model_version": version,
        "model_name": name,
        "threshold": threshold,
        "features": FEATURE_COLUMNS,
        "data_range": {"start": str(df["event_date"].min()), "end": str(df["event_date"].max())},
        "split_rows": {"train": len(train), "validation": len(val), "test": len(test)},
        "validation_pr_auc_by_model": comparison,
        "test_metrics": _metrics(y_test, test_scores, threshold),
        "baseline_amount_p95_test_metrics": baseline,
        "test_fraud_rate": round(float(y_test.mean()), 4),
    }

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, artifacts_dir / MODEL_FILE)
    (artifacts_dir / METADATA_FILE).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    log.info("Modelo %s (%s) salvo em %s", name, version, artifacts_dir)
    return metadata


def train_from_mart(artifacts_dir: Path) -> dict:
    from pipeline import db

    with db.connect() as conn:
        df = db.fetch_df(conn, f"SELECT event_date, {', '.join(FEATURE_COLUMNS)}, {TARGET_COLUMN} "
                               "FROM mart.fct_transactions")
    if df.empty:
        raise ValueError("mart.fct_transactions esta vazio. Rode o pipeline (ou um backfill) antes.")
    return train_from_frame(df, artifacts_dir)
