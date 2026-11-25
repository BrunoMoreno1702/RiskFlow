"""API de origem: expoe as transacoes de um dia, como um sistema transacional faria."""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query

from source_api.generator import DEFAULT_CUSTOMERS, generate_transactions

app = FastAPI(title="RiskFlow Source API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/transactions")
def get_transactions(
    day: date = Query(alias="date", description="Dia das transacoes (YYYY-MM-DD)."),
    customers: int = Query(DEFAULT_CUSTOMERS, ge=1, le=5000),
) -> dict:
    if day > date.today():
        raise HTTPException(status_code=422, detail="Nao existem transacoes para datas futuras.")

    data = generate_transactions(day, customers=customers)
    return {"date": day.isoformat(), "count": len(data), "data": data}
