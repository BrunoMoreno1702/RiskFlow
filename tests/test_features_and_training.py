from datetime import date, timedelta

import pandas as pd

from ml.features import FEATURE_COLUMNS, build_features
from ml.model import load_model
from ml.train import train_from_frame
from pipeline.transform import normalize
from source_api.generator import generate_transactions


def _tx(tx_id, ts, amount, category="food", customer="C1"):
    return {
        "transaction_id": tx_id,
        "customer_id": customer,
        "amount": amount,
        "merchant": "m",
        "category": category,
        "card_network": "Visa",
        "event_ts": pd.Timestamp(ts),
    }


def test_features_use_only_past_transactions():
    history = pd.DataFrame([_tx("h1", "2026-10-01 09:00", 100), _tx("h2", "2026-10-01 09:30", 300)])
    current = pd.DataFrame(
        [_tx("c1", "2026-10-01 10:00", 1000, "electronics"), _tx("c2", "2026-10-01 10:05", 50)]
    )
    out = build_features(current, history).set_index("transaction_id")

    c1 = out.loc["c1"]
    assert c1["cust_tx_count_1h"] == 2  # h1 e h2, nao ele mesmo
    assert c1["cust_avg_amount_30d"] == 200
    assert c1["amount_vs_cust_avg"] == 5
    assert c1["is_new_category_for_customer"] == 1

    # c2 ve c1 no passado, mas c1 nunca ve c2 (sem vazamento do futuro).
    # Janela de 1h de c2 (10:05) e [09:05, 10:05): h2 e c1 entram, h1 (09:00) nao.
    assert out.loc["c2"]["cust_tx_count_1h"] == 2
    assert out.loc["c2"]["cust_tx_count_30d"] == 3


def test_first_transaction_of_customer_has_neutral_features():
    out = build_features(pd.DataFrame([_tx("c1", "2026-10-01 10:00", 80)]))
    row = out.iloc[0]
    assert row["cust_tx_count_30d"] == 0
    assert row["amount_vs_cust_avg"] == 1
    assert row["is_new_category_for_customer"] == 0
    assert set(FEATURE_COLUMNS) <= set(out.columns)


def test_training_end_to_end_beats_baseline(tmp_path):
    start = date(2026, 6, 1)
    staged = pd.concat(
        [normalize(generate_transactions(start + timedelta(days=d), customers=300)) for d in range(60)],
        ignore_index=True,
    )
    features = build_features(staged)

    metadata = train_from_frame(features, tmp_path)
    model = load_model(tmp_path)

    assert model.version == metadata["model_version"]
    assert 0 < model.threshold < 1
    # O modelo precisa justificar sua existencia contra a regra simples de valor alto.
    assert metadata["test_metrics"]["pr_auc"] > metadata["baseline_amount_p95_test_metrics"]["pr_auc"]
