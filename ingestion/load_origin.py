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
VALUES (?, ?, ?, ?, ?, ?, ?);
"""

SELECT_EXISTING_ORIGIN_SQL_TEMPLATE = """
SELECT transaction_id
FROM transactions_origin
WHERE transaction_id IN ({placeholders});
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
    return (
        str(row["transaction_id"]),
        str(row["customer_id"]),
        float(row["amount"]),
        str(row["merchant"]),
        str(row["category"]),
        pd.to_datetime(row["timestamp"]).to_pydatetime(),
        int(row["is_fraud"])
    )


def _chunked(values, chunk_size):
    for start in range(0, len(values), chunk_size):
        yield values[start:start + chunk_size]


def load_transactions_origin(df: pd.DataFrame):
    _validate_required_columns(df)

    # Evita duplicidade dentro do proprio lote retornado pela API.
    records_by_transaction_id = {}

    for _, row in df.iterrows():
        record = _build_origin_record(row)
        transaction_id = record[0]

        if transaction_id not in records_by_transaction_id:
            records_by_transaction_id[transaction_id] = record

    transaction_ids = list(records_by_transaction_id.keys())

    if not transaction_ids:
        print("transactions_origin: nenhum registro novo para processar.")
        return []

    connection = get_connection()

    try:
        cursor = connection.cursor()
        existing_ids = set()

        # Consulta em blocos para manter estabilidade com lotes grandes.
        for chunk in _chunked(transaction_ids, 1000):
            placeholders = ", ".join("?" for _ in chunk)
            select_existing_sql = SELECT_EXISTING_ORIGIN_SQL_TEMPLATE.format(placeholders=placeholders)
            cursor.execute(select_existing_sql, chunk)
            existing_ids.update(str(row.transaction_id) for row in cursor.fetchall())

        # So segue para a proxima camada com o que realmente entrou na origem.
        inserted_transaction_ids = [
            transaction_id
            for transaction_id in transaction_ids
            if transaction_id not in existing_ids
        ]

        if not inserted_transaction_ids:
            print("transactions_origin: nenhum registro novo para processar.")
            return []

        records_to_insert = [records_by_transaction_id[transaction_id] for transaction_id in inserted_transaction_ids]

        cursor.fast_executemany = True
        cursor.executemany(INSERT_ORIGIN_SQL, records_to_insert)

        connection.commit()

        print(f"transactions_origin: {len(inserted_transaction_ids)} registros inseridos.")
        return inserted_transaction_ids

    finally:
        connection.close()
