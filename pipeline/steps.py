"""Etapas do pipeline diario. Cada etapa processa UM dia e e idempotente:
reexecutar o mesmo dia substitui o resultado anterior em vez de duplicar.

Estas funcoes sao chamadas tanto pela CLI (pipeline/run.py) quanto pela DAG do Airflow.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time

from psycopg.types.json import Jsonb

from ml.features import FEATURE_COLUMNS, HISTORY_WINDOW, ID_COLUMNS, TARGET_COLUMN, build_features
from pipeline import db, quality
from pipeline.extract import fetch_transactions
from pipeline.transform import STAGING_COLUMNS, normalize

log = logging.getLogger(__name__)

MART_COLUMNS = ID_COLUMNS + FEATURE_COLUMNS + [TARGET_COLUMN]


def extract_and_load_raw(day: date) -> int:
    records = fetch_transactions(day)
    with db.connect() as conn:
        conn.execute("DELETE FROM raw.transactions WHERE batch_date = %s", (day,))
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO raw.transactions (batch_date, payload) VALUES (%s, %s)",
                [(day, Jsonb(r)) for r in records],
            )
    log.info("raw: %s registros para %s", len(records), day)
    return len(records)


def stage(day: date) -> int:
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT payload FROM raw.transactions WHERE batch_date = %s ORDER BY id", (day,))
            records = [row[0] for row in cur.fetchall()]

        df = normalize(records)
        results = quality.run_checks(df, day)
        for r in results:
            log.info("quality %-26s %s", r.name, "OK" if r.passed else f"FALHOU: {r.detail}")
        quality.enforce(results)

        rows = [
            tuple(None if v is None else (v.item() if hasattr(v, "item") else v) for v in row)
            for row in df[STAGING_COLUMNS].astype(object).itertuples(index=False, name=None)
        ]
        conn.execute("DELETE FROM staging.transactions WHERE event_date = %s", (day,))
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO staging.transactions ({', '.join(STAGING_COLUMNS)}) "
                f"VALUES ({', '.join(['%s'] * len(STAGING_COLUMNS))})",
                rows,
            )
    log.info("staging: %s registros para %s", len(rows), day)
    return len(rows)


def build_mart(day: date) -> int:
    day_start = datetime.combine(day, time.min)
    with db.connect() as conn:
        frame = db.fetch_df(
            conn,
            """
            SELECT transaction_id, customer_id, amount, merchant, category, card_network,
                   event_ts, is_fraud
            FROM staging.transactions
            WHERE event_ts >= %s AND event_date <= %s
            """,
            (day_start - HISTORY_WINDOW, day),
        )
        current = frame[frame["event_ts"] >= day_start]
        history = frame[frame["event_ts"] < day_start]
        features = build_features(current, history)

        rows = [
            tuple(v.item() if hasattr(v, "item") else v for v in row)
            for row in features[MART_COLUMNS].astype(object).itertuples(index=False, name=None)
        ]
        conn.execute("DELETE FROM mart.fct_transactions WHERE event_date = %s", (day,))
        with conn.cursor() as cur:
            cur.executemany(
                f"INSERT INTO mart.fct_transactions ({', '.join(MART_COLUMNS)}) "
                f"VALUES ({', '.join(['%s'] * len(MART_COLUMNS))})",
                rows,
            )
    log.info("mart: %s registros para %s (historico: %s)", len(rows), day, len(history))
    return len(rows)


def score(day: date) -> int:
    from ml.model import load_model  # import tardio: so carrega scikit-learn quando necessario

    model = load_model()
    with db.connect() as conn:
        frame = db.fetch_df(
            conn,
            f"SELECT {', '.join(['transaction_id', *FEATURE_COLUMNS])} "
            "FROM mart.fct_transactions WHERE event_date = %s",
            (day,),
        )
        if frame.empty:
            log.info("score: nada para pontuar em %s", day)
            return 0

        scores = model.score(frame)
        conn.execute(
            "DELETE FROM mart.fraud_scores s USING mart.fct_transactions f "
            "WHERE s.transaction_id = f.transaction_id AND f.event_date = %s",
            (day,),
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO mart.fraud_scores "
                "(transaction_id, fraud_score, prediction, threshold, model_version) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    (tx, float(s), int(s >= model.threshold), model.threshold, model.version)
                    for tx, s in zip(frame["transaction_id"], scores, strict=True)
                ],
            )
    log.info("score: %s transacoes pontuadas em %s (modelo %s)", len(frame), day, model.version)
    return len(frame)
