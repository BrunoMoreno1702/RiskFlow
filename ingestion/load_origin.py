import pandas as pd
from database.connection import get_connection

INSERT_ORIGIN_SQL = """
INSERT INTO transactions_origin (
    transaction_id,
    customer_id,
    amount,
    merchant,
    category,
    [timestamp],
    is_fraud
)
SELECT
    ?, ?, ?, ?, ?, ?, ?
WHERE NOT EXISTS (
    SELECT 1
    FROM transactions_origin
    WHERE transaction_id = ?
);
"""


def _validate_required_columns(df: pd.DataFrame):
    required_columns = [
        "transaction_id",
        "customer_id",
        "amount",
        "merchant",
        "category",
        "timestamp",
        "is_fraud"
    ]

    missing_columns = [column for column in required_columns if column not in df.columns]

    if missing_columns:
        raise ValueError(f"Colunas ausentes no DataFrame: {missing_columns}")


def _build_origin_record(row):
    transaction_id = str(row["transaction_id"])
    customer_id = str(row["customer_id"])
    amount = float(row["amount"])
    merchant = str(row["merchant"])
    category = str(row["category"])
    timestamp = pd.to_datetime(row["timestamp"]).to_pydatetime()
    is_fraud = int(row["is_fraud"])

    return (
        transaction_id,
        customer_id,
        amount,
        merchant,
        category,
        timestamp,
        is_fraud,
        transaction_id
    )


def load_transactions_origin(df: pd.DataFrame):
    _validate_required_columns(df)

    records = []

    for _, row in df.iterrows():
        records.append(_build_origin_record(row))

    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.fast_executemany = True

        cursor.executemany(INSERT_ORIGIN_SQL, records)

        connection.commit()

        print(f"transactions_origin: {len(records)} registros processados.")

    finally:
        connection.close()