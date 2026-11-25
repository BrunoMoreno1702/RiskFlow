from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

import pandas as pd
import psycopg

from pipeline import config

log = logging.getLogger(__name__)


def connect() -> psycopg.Connection:
    return psycopg.connect(config.DATABASE_URL)


def apply_schema(conn: psycopg.Connection) -> None:
    """Executa os scripts de sql/ em ordem. Os scripts sao idempotentes."""
    for script in sorted(config.SQL_DIR.glob("*.sql")):
        log.info("Aplicando %s", script.name)
        conn.execute(script.read_text(encoding="utf-8"))
    conn.commit()


def fetch_df(conn: psycopg.Connection, sql: str, params: Sequence[Any] | None = None) -> pd.DataFrame:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        columns = [d.name for d in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=columns)
    # UUID e Decimal do Postgres -> tipos simples para pandas/scikit-learn.
    for col in ("transaction_id",):
        if col in df.columns:
            df[col] = df[col].astype(str)
    if "amount" in df.columns:
        df["amount"] = df["amount"].astype(float)
    return df
