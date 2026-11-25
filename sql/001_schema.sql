-- Schema do RiskFlow. Idempotente: pode ser executado varias vezes.
-- Camadas:
--   raw     -> payload exatamente como chegou da origem (fonte da verdade, permite replay)
--   staging -> dados tipados, validados e deduplicados
--   mart    -> tabela fato com features e scores do modelo, pronta para consumo

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE TABLE IF NOT EXISTS raw.transactions (
    id           BIGSERIAL PRIMARY KEY,
    batch_date   DATE        NOT NULL,
    payload      JSONB       NOT NULL,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_raw_transactions_batch_date ON raw.transactions (batch_date);

CREATE TABLE IF NOT EXISTS staging.transactions (
    transaction_id  UUID          PRIMARY KEY,
    customer_id     TEXT          NOT NULL,
    amount          NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    merchant        TEXT          NOT NULL,
    category        TEXT          NOT NULL,
    card_network    TEXT          NOT NULL,
    event_ts        TIMESTAMP     NOT NULL,
    event_date      DATE          NOT NULL,
    is_fraud        SMALLINT      NOT NULL CHECK (is_fraud IN (0, 1)),
    loaded_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_staging_transactions_event_date ON staging.transactions (event_date);
CREATE INDEX IF NOT EXISTS ix_staging_transactions_customer_ts ON staging.transactions (customer_id, event_ts);

CREATE TABLE IF NOT EXISTS mart.fct_transactions (
    transaction_id                UUID             PRIMARY KEY,
    customer_id                   TEXT             NOT NULL,
    event_ts                      TIMESTAMP        NOT NULL,
    event_date                    DATE             NOT NULL,
    merchant                      TEXT             NOT NULL,
    category                      TEXT             NOT NULL,
    card_network                  TEXT             NOT NULL,
    amount                        DOUBLE PRECISION NOT NULL,
    amount_log                    DOUBLE PRECISION NOT NULL,
    hour                          SMALLINT         NOT NULL,
    is_night                      SMALLINT         NOT NULL,
    is_weekend                    SMALLINT         NOT NULL,
    cust_tx_count_1h              INTEGER          NOT NULL,
    cust_tx_count_24h             INTEGER          NOT NULL,
    cust_tx_count_30d             INTEGER          NOT NULL,
    cust_avg_amount_30d           DOUBLE PRECISION NOT NULL,
    amount_vs_cust_avg            DOUBLE PRECISION NOT NULL,
    is_new_category_for_customer  SMALLINT         NOT NULL,
    is_fraud                      SMALLINT         NOT NULL,
    built_at                      TIMESTAMPTZ      NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_fct_transactions_event_date ON mart.fct_transactions (event_date);

-- Reconstruir um dia do mart apaga os scores daquele dia (ON DELETE CASCADE),
-- garantindo que nunca exista score calculado sobre features antigas.
CREATE TABLE IF NOT EXISTS mart.fraud_scores (
    transaction_id  UUID             PRIMARY KEY
                    REFERENCES mart.fct_transactions (transaction_id) ON DELETE CASCADE,
    fraud_score     DOUBLE PRECISION NOT NULL,
    prediction      SMALLINT         NOT NULL,
    threshold       DOUBLE PRECISION NOT NULL,
    model_version   TEXT             NOT NULL,
    scored_at       TIMESTAMPTZ      NOT NULL DEFAULT now()
);
