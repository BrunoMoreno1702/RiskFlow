from babel.dates import format_date

from database.connection import get_connection

SELECT_ORIGIN_SQL = """
SELECT
    origin.transaction_id,
    origin.customer_id,
    origin.amount,
    origin.merchant,
    origin.category,
    origin.[timestamp] AS data_hora,
    origin.is_fraud
FROM transactions_origin origin
WHERE NOT EXISTS (
    SELECT 1
    FROM transactions_prod prod
    WHERE prod.id_transacao = origin.transaction_id
);
"""

SELECT_ORIGIN_BATCH_SQL_TEMPLATE = """
SELECT
    origin.transaction_id,
    origin.customer_id,
    origin.amount,
    origin.merchant,
    origin.category,
    origin.[timestamp] AS data_hora,
    origin.is_fraud
FROM transactions_origin origin
WHERE origin.transaction_id IN ({placeholders})
AND NOT EXISTS (
    SELECT 1
    FROM transactions_prod prod
    WHERE prod.id_transacao = origin.transaction_id
);
"""

INSERT_PROD_SQL = """
INSERT INTO transactions_prod (
    id_transacao,
    id_cliente,
    valor,
    estabelecimento,
    categoria,
    data_hora_transacao,
    hora_transacao,
    dia_transacao,
    mes_transacao,
    indicativo_fraude
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def _build_prod_record(row):
    data_hora = row.data_hora
    hora_transacao = data_hora.time().replace(microsecond=0)
    dia_transacao = data_hora.strftime("%d/%m")
    # Mes por extenso em pt-BR para manter o layout da camada de consumo.
    mes_transacao = format_date(data_hora.date(), "MMMM", locale="pt_BR")

    return (
        row.transaction_id,
        row.customer_id,
        float(row.amount),
        row.merchant,
        row.category,
        data_hora,
        hora_transacao,
        dia_transacao,
        mes_transacao,
        int(row.is_fraud)
    )


def _fetch_origin_rows(cursor, transaction_ids=None):
    # Modo completo: usado para reconciliacao sem filtro por lote.
    if not transaction_ids:
        cursor.execute(SELECT_ORIGIN_SQL)
        return cursor.fetchall()

    # Remove repetidos preservando ordem de entrada do lote.
    unique_ids = list(dict.fromkeys(transaction_ids))
    rows = []
    chunk_size = 1000

    for start in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[start:start + chunk_size]
        placeholders = ", ".join("?" for _ in chunk)
        query = SELECT_ORIGIN_BATCH_SQL_TEMPLATE.format(placeholders=placeholders)
        cursor.execute(query, chunk)
        rows.extend(cursor.fetchall())

    return rows


def load_transactions_prod(transaction_ids=None):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        origin_rows = _fetch_origin_rows(cursor, transaction_ids=transaction_ids)

        if not origin_rows:
            print("transactions_prod: nenhum registro novo para processar.")
            return

        records = []

        for row in origin_rows:
            records.append(_build_prod_record(row))

        cursor.fast_executemany = True
        cursor.executemany(INSERT_PROD_SQL, records)

        connection.commit()

        print(f"transactions_prod: {len(records)} registros inseridos.")

    finally:
        connection.close()
