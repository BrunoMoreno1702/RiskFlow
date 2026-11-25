from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient

from source_api.generator import generate_transactions
from source_api.main import app

DAY = date(2026, 10, 1)


def test_same_day_is_deterministic():
    assert generate_transactions(DAY, customers=50) == generate_transactions(DAY, customers=50)


def test_different_days_differ():
    assert generate_transactions(DAY, customers=50) != generate_transactions(
        DAY + timedelta(days=1), customers=50
    )


def test_ids_unique_across_many_days():
    ids = [
        tx["transaction_id"]
        for offset in range(30)
        for tx in generate_transactions(DAY + timedelta(days=offset), customers=200)
    ]
    assert len(ids) == len(set(ids))


def test_timestamps_stay_inside_the_day():
    for tx in generate_transactions(DAY, customers=300):
        assert datetime.fromisoformat(tx["timestamp"]).date() == DAY


def test_fraud_rate_is_rare_but_present():
    txs = [tx for offset in range(30) for tx in generate_transactions(DAY + timedelta(days=offset))]
    rate = sum(tx["is_fraud"] for tx in txs) / len(txs)
    assert 0.002 < rate < 0.03


def test_api_returns_generator_output():
    client = TestClient(app)
    response = client.get("/transactions", params={"date": DAY.isoformat(), "customers": 20})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["data"])
    assert body["data"] == generate_transactions(DAY, customers=20)


def test_api_rejects_future_dates():
    client = TestClient(app)
    future = date.today() + timedelta(days=1)
    assert client.get("/transactions", params={"date": future.isoformat()}).status_code == 422
