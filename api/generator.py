import random
from datetime import datetime, timedelta

MERCHANTS = {
    "Amazon": {"category": "shopping", "min_amount": 20, "max_amount": 300},
    "Uber": {"category": "transport", "min_amount": 8, "max_amount": 90},
    "Shell": {"category": "fuel", "min_amount": 50, "max_amount": 500},
    "Walmart": {"category": "shopping", "min_amount": 20, "max_amount": 400},
    "Starbucks": {"category": "food", "min_amount": 10, "max_amount": 60},
    "McDonalds": {"category": "food", "min_amount": 15, "max_amount": 80},
    "Subway": {"category": "food", "min_amount": 12, "max_amount": 70},
    "Carrefour": {"category": "shopping", "min_amount": 25, "max_amount": 350}
}


def _random_timestamp(min_hour, max_hour, max_day_offset):
    return datetime.now().replace(
        hour=random.randint(min_hour, max_hour),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=0
    ) - timedelta(days=random.randint(0, max_day_offset))


def _build_transaction(customer_id, merchant, amount, timestamp, is_fraud):
    merchant_info = MERCHANTS[merchant]

    return {
        "transaction_id": f"tx_{random.randint(100000, 999999)}",
        "customer_id": customer_id,
        "amount": amount,
        "merchant": merchant,
        "category": merchant_info["category"],
        "timestamp": timestamp.isoformat(),
        "is_fraud": is_fraud
    }


def generate_normal_transaction(customer_id):
    merchant = random.choice(list(MERCHANTS.keys()))
    merchant_info = MERCHANTS[merchant]
    amount = round(random.uniform(merchant_info["min_amount"], merchant_info["max_amount"]), 2)
    timestamp = _random_timestamp(min_hour=8, max_hour=22, max_day_offset=30)

    return _build_transaction(customer_id, merchant, amount, timestamp, is_fraud=0)


def generate_fraud_transaction(customer_id):
    merchant = random.choice(list(MERCHANTS.keys()))
    amount = round(random.uniform(1000, 5000), 2)
    timestamp = _random_timestamp(min_hour=2, max_hour=5, max_day_offset=90)

    return _build_transaction(customer_id, merchant, amount, timestamp, is_fraud=1)


def generate_customer_transactions(customer_id):
    transactions = []
    normal_count = random.randint(7, 22)

    for _ in range(normal_count):
        transactions.append(generate_normal_transaction(customer_id))

    # Mantemos 20% dos clientes com fraudes para preservar a distribuição histórica do dataset.
    if random.random() < 0.2:
        fraud_count = random.randint(3, 7)
        for _ in range(fraud_count):
            transactions.append(generate_fraud_transaction(customer_id))

    return transactions