from __future__ import annotations

from datetime import date

import requests

from pipeline import config


class SourceContractError(Exception):
    """A resposta da origem nao segue o contrato esperado."""


def fetch_transactions(day: date, customers: int | None = None) -> list[dict]:
    response = requests.get(
        f"{config.SOURCE_API_URL}/transactions",
        params={"date": day.isoformat(), "customers": customers or config.SOURCE_CUSTOMERS},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload.get("data"), list):
        raise SourceContractError("Resposta sem a lista 'data'.")
    if payload.get("date") != day.isoformat():
        raise SourceContractError(f"Origem devolveu a data {payload.get('date')}, esperado {day}.")
    if payload.get("count") != len(payload["data"]):
        raise SourceContractError("Campo 'count' nao bate com o tamanho de 'data'.")
    return payload["data"]
