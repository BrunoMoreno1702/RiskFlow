from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from api.generator import generate_customer_transactions
from ml.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES, TARGET_COLUMN, build_feature_frame


def _generate_training_dataframe(customers: int) -> pd.DataFrame:
    transactions: list[dict] = []

    for i in range(1, customers + 1):
        customer_id = f"CUST_{i:05d}"
        transactions.extend(generate_customer_transactions(customer_id))

    df = pd.DataFrame(transactions)
    if df.empty:
        raise ValueError("A geração de dados retornou DataFrame vazio.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def _split_temporal(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    total = len(df)
    if total < 100:
        raise ValueError("São necessárias pelo menos 100 transações para split temporal confiável.")

    train_end = int(total * 0.70)
    val_end = int(total * 0.85)

    train_df = df.iloc[:train_end].copy()
    val_df = df.iloc[train_end:val_end].copy()
    test_df = df.iloc[val_end:].copy()

    return train_df, val_df, test_df


def _build_model_candidates(random_state: int) -> dict[str, Pipeline]:
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )

    logistic = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_state)),
        ]
    )

    forest = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=400,
                    max_depth=14,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    return {
        "logistic_regression": logistic,
        "random_forest": forest,
    }


def _evaluate(y_true: pd.Series, scores: pd.Series, threshold: float) -> dict[str, float]:
    predictions = (scores >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(y_true, scores)),
        "pr_auc": float(average_precision_score(y_true, scores)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
    }


def _best_threshold_by_f1(y_true: pd.Series, scores: pd.Series) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, scores)
    if len(thresholds) == 0:
        return 0.5

    f1_values = (2 * precision[:-1] * recall[:-1]) / (precision[:-1] + recall[:-1] + 1e-12)
    best_idx = int(f1_values.argmax())
    return float(thresholds[best_idx])


def train(customers: int, artifacts_dir: Path, random_state: int) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    raw_df = _generate_training_dataframe(customers=customers)
    train_df, val_df, test_df = _split_temporal(raw_df)

    x_train, feature_stats = build_feature_frame(train_df, training=True)
    x_val, _ = build_feature_frame(val_df, stats=feature_stats, training=False)
    x_test, _ = build_feature_frame(test_df, stats=feature_stats, training=False)

    y_train = train_df[TARGET_COLUMN].astype(int)
    y_val = val_df[TARGET_COLUMN].astype(int)
    y_test = test_df[TARGET_COLUMN].astype(int)

    candidates = _build_model_candidates(random_state=random_state)
    best_name = ""
    best_model: Pipeline | None = None
    best_threshold = 0.5
    best_val_metrics: dict[str, float] | None = None
    best_test_metrics: dict[str, float] | None = None

    for model_name, model in candidates.items():
        model.fit(x_train[FEATURE_COLUMNS], y_train)
        val_scores = pd.Series(model.predict_proba(x_val[FEATURE_COLUMNS])[:, 1], index=x_val.index)
        threshold = _best_threshold_by_f1(y_val, val_scores)
        val_metrics = _evaluate(y_val, val_scores, threshold)

        if best_val_metrics is None or val_metrics["pr_auc"] > best_val_metrics["pr_auc"]:
            best_name = model_name
            best_model = model
            best_threshold = threshold
            best_val_metrics = val_metrics

            test_scores = pd.Series(model.predict_proba(x_test[FEATURE_COLUMNS])[:, 1], index=x_test.index)
            best_test_metrics = _evaluate(y_test, test_scores, threshold)

    if best_model is None or best_val_metrics is None or best_test_metrics is None:
        raise RuntimeError("Não foi possível selecionar um modelo vencedor.")

    model_path = artifacts_dir / "model.joblib"
    stats_path = artifacts_dir / "feature_stats.json"
    metadata_path = artifacts_dir / "metadata.json"

    joblib.dump(best_model, model_path)

    with stats_path.open("w", encoding="utf-8") as file:
        json.dump(feature_stats, file, ensure_ascii=True, indent=2)

    metadata = {
        "model_name": best_name,
        "threshold": best_threshold,
        "features": FEATURE_COLUMNS,
        "customers_used": customers,
        "split": {"train": len(train_df), "validation": len(val_df), "test": len(test_df)},
        "metrics": {
            "validation": best_val_metrics,
            "test": best_test_metrics,
        },
    }
    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=True, indent=2)

    print("Treinamento concluido.")
    print(f"Modelo escolhido: {best_name}")
    print(f"Threshold: {best_threshold:.4f}")
    print(f"PR-AUC validacao: {best_val_metrics['pr_auc']:.4f}")
    print(f"PR-AUC teste: {best_test_metrics['pr_auc']:.4f}")
    print(f"Artefatos salvos em: {artifacts_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Treina modelo de fraude com split temporal e salva artefatos.")
    parser.add_argument("--customers", type=int, default=1000, help="Quantidade de clientes sinteticos para treino.")
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=Path("ml") / "artifacts",
        help="Diretorio de saida para model.joblib e metadados.",
    )
    parser.add_argument("--random-state", type=int, default=42, help="Seed de reproducibilidade.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(customers=args.customers, artifacts_dir=args.artifacts_dir, random_state=args.random_state)

