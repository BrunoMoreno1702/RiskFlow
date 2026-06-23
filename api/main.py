from fastapi import FastAPI

from api.generator import generate_customer_transactions

app = FastAPI()


def _build_customer_id(index):
    return f"CUST_{index:05d}"


@app.get("/")
def home():
    return {"status": "ok"}


@app.get("/transactions")
def get_transactions(customers: int = 100):
    data = []

    for i in range(1, customers + 1):
        customer_id = _build_customer_id(i)
        data.extend(generate_customer_transactions(customer_id))

    return {
        "customers": customers,
        "transactions": len(data),
        "data": data
    }
