import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from database.connection import get_connection

SELECT_TRAINING_DATA_SQL = """
SELECT
    id_cliente,
    valor,
    data_hora_transacao,
    indicativo_fraude
FROM transactions_prod
WHERE indicativo_fraude IN (0, 1);
"""

SELECT_SCORING_DATA_SQL = """
SELECT
    id_transacao,
    id_cliente,
    valor,
    data_hora_transacao
FROM transactions_prod;
"""

UPDATE_PREDICTION_SQL = """
UPDATE transactions_prod
SET
    probabilidade_fraude_ml = ?,
    indicativo_fraude_ml = ?,
    data_predicao_ml = SYSUTCDATETIME()
WHERE id_transacao = ?;
"""


def load_training_dataframe():
    connection = get_connection()

    try:
        dataframe = pd.read_sql(SELECT_TRAINING_DATA_SQL, connection)
    finally:
        connection.close()

    if dataframe.empty:
        raise ValueError("A tabela transactions_prod não retornou dados para treino.")

    dataframe["data_hora_transacao"] = pd.to_datetime(dataframe["data_hora_transacao"], errors="coerce")
    dataframe = dataframe.dropna(subset=["id_cliente", "valor", "data_hora_transacao", "indicativo_fraude"])

    if dataframe.empty:
        raise ValueError("Não há dados válidos após o pré-processamento inicial.")

    return dataframe


# Feature temporal: média de valor dos 7 dias anteriores por cliente (sem vazamento).
def _compute_customer_recent_average_7d(feature_frame):
    sorted_frame = feature_frame.sort_values(["id_cliente", "data_hora_transacao"]).copy()
    sorted_frame["valor_medio_7d_cliente"] = pd.NA

    for _, customer_frame in sorted_frame.groupby("id_cliente", sort=False):
        customer_frame = customer_frame.sort_values("data_hora_transacao").copy()
        customer_frame["_orig_index"] = customer_frame.index

        rolling_mean = (
            customer_frame.set_index("data_hora_transacao")["valor"]
                        # shift(1) garante que a transação atual não use a si mesma no histórico.
.shift(1)
            .rolling("7D")
            .mean()
            .to_numpy()
        )

        sorted_frame.loc[customer_frame["_orig_index"], "valor_medio_7d_cliente"] = rolling_mean

    sorted_frame["valor_medio_7d_cliente"] = sorted_frame["valor_medio_7d_cliente"].fillna(sorted_frame["valor"])

    return sorted_frame


def build_features_and_target(dataframe):
    feature_frame = dataframe.copy()
    feature_frame["hora"] = feature_frame["data_hora_transacao"].dt.hour
    feature_frame["is_madrugada"] = feature_frame["hora"].between(0, 5).astype(int)
    feature_frame = _compute_customer_recent_average_7d(feature_frame)

    X = feature_frame[["hora", "is_madrugada", "valor_medio_7d_cliente"]]
    y = feature_frame["indicativo_fraude"].astype(int)

    if y.nunique() < 2:
        raise ValueError("Treino supervisionado requer as duas classes (0 e 1) em indicativo_fraude.")

    return X, y


def build_pipeline():
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ]
    )


def train_and_evaluate(test_size):
    dataframe = load_training_dataframe()
    X, y = build_features_and_target(dataframe)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=42,
        stratify=y,
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    probabilities = pipeline.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics = {
        "features": ["hora", "is_madrugada", "valor_medio_7d_cliente"],
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "classification_report": classification_report(y_test, predictions, digits=4),
    }

    return pipeline, metrics


# Bloco opcional para gravar score e classe prevista na tabela de produção.
def fill_predictions_in_db(model, threshold=0.5):
    connection = get_connection()

    try:
        scoring_df = pd.read_sql(SELECT_SCORING_DATA_SQL, connection)

        if scoring_df.empty:
            print("Sem dados para scoring na transactions_prod.")
            return

        scoring_df["data_hora_transacao"] = pd.to_datetime(scoring_df["data_hora_transacao"], errors="coerce")
        scoring_df = scoring_df.dropna(subset=["id_transacao", "id_cliente", "valor", "data_hora_transacao"])

        if scoring_df.empty:
            print("Sem dados válidos para scoring após limpeza.")
            return

        scoring_df["hora"] = scoring_df["data_hora_transacao"].dt.hour
        scoring_df["is_madrugada"] = scoring_df["hora"].between(0, 5).astype(int)
        scoring_df = _compute_customer_recent_average_7d(scoring_df)

        X_score = scoring_df[["hora", "is_madrugada", "valor_medio_7d_cliente"]]

        probabilities = model.predict_proba(X_score)[:, 1]
        predictions = (probabilities >= threshold).astype(int)

        updates = [
            (round(float(probability) * 100, 3), int(prediction), str(transaction_id))
            for probability, prediction, transaction_id in zip(
                probabilities,
                predictions,
                scoring_df["id_transacao"],
            )
        ]

        cursor = connection.cursor()
        cursor.fast_executemany = True
        cursor.executemany(UPDATE_PREDICTION_SQL, updates)
        connection.commit()

        print(f"Predições ML atualizadas na base: {len(updates)} registros.")

    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description="Treina modelo supervisionado de fraude com foco em horário/madrugada.")
    parser.add_argument("--test-size", type=float, default=0.2, help="Proporção do conjunto de teste.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="ml\\artifacts",
        help="Pasta para salvar artefatos do modelo.",
    )

    args = parser.parse_args()

    if not 0 < args.test_size < 1:
        raise ValueError("--test-size deve estar entre 0 e 1.")

    model, metrics = train_and_evaluate(test_size=args.test_size)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_path = output_dir / "fraud_model.joblib"
    metrics_path = output_dir / "metrics.json"

    joblib.dump(model, model_path)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Modelo salvo em: {model_path}")
    print(f"Métricas salvas em: {metrics_path}")
    print("\nClassification report:\n")
    print(metrics["classification_report"])
    print(f"ROC AUC: {metrics['roc_auc']:.4f}")
    print(f"PR AUC: {metrics['pr_auc']:.4f}")

    # Predições do ML no banco:
    fill_predictions_in_db(model, threshold=0.5)


if __name__ == "__main__":
    main()





