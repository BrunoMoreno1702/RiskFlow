"""Gerador deterministico de transacoes de cartao.

Simula o sistema de origem. A mesma (data, seed, quantidade de clientes) sempre
produz exatamente as mesmas transacoes, o que torna o pipeline reprocessavel:
reexecutar um dia ou fazer backfill nao gera dados diferentes.

Padroes de fraude sao comportamentais (rajada de compras pequenas seguida de uma
grande, valor muito acima do perfil do cliente, categoria incomum, madrugada) e
existem transacoes legitimas parecidas com fraude (compras grandes e noturnas),
para que o problema nao seja trivialmente separavel por um unico atributo.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

DEFAULT_CUSTOMERS = 500
DEFAULT_SEED = 42

# Namespace fixo: transaction_id e derivado de (seed, data, cliente, sequencia).
ID_NAMESPACE = uuid.UUID("6f1c0d1e-8a2b-4c3d-9e4f-5a6b7c8d9e0f")

# categoria -> (estabelecimentos, valor mediano em BRL, dispersao log-normal)
CATEGORIES: dict[str, tuple[tuple[str, ...], float, float]] = {
    "grocery": (("Carrefour", "Pao de Acucar", "Assai"), 90.0, 0.6),
    "food": (("iFood", "McDonalds", "Starbucks"), 45.0, 0.5),
    "transport": (("Uber", "99"), 25.0, 0.5),
    "fuel": (("Shell", "Ipiranga"), 180.0, 0.4),
    "shopping": (("Amazon", "Mercado Livre", "Magalu"), 150.0, 0.8),
    "electronics": (("Kabum", "Fast Shop"), 900.0, 0.7),
}
CARD_NETWORKS = ("Visa", "Mastercard", "Elo", "American Express")

# Probabilidade de um cliente sofrer um episodio de fraude em um dia.
FRAUD_EPISODE_PROB = 0.004
LEGIT_NIGHT_PROB = 0.03
LEGIT_BIG_PURCHASE_PROB = 0.02


@dataclass(frozen=True)
class CustomerProfile:
    customer_id: str
    spend_multiplier: float
    daily_rate: float
    active_hours: tuple[int, int]
    favorite_categories: tuple[str, ...]
    card_network: str


def customer_id_for(index: int) -> str:
    return f"CUST_{index:05d}"


def customer_profile(index: int, seed: int = DEFAULT_SEED) -> CustomerProfile:
    rng = random.Random(f"profile|{seed}|{index}")
    return CustomerProfile(
        customer_id=customer_id_for(index),
        spend_multiplier=math.exp(rng.gauss(0.0, 0.4)),
        daily_rate=rng.uniform(0.3, 2.5),
        active_hours=(rng.randint(6, 10), rng.randint(19, 23)),
        favorite_categories=tuple(rng.sample(sorted(CATEGORIES), 3)),
        card_network=rng.choice(CARD_NETWORKS),
    )


def _poisson(rng: random.Random, lam: float) -> int:
    # Algoritmo de Knuth: suficiente para lambdas pequenos.
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _amount(rng: random.Random, category: str, multiplier: float) -> float:
    _, median, sigma = CATEGORIES[category]
    return round(max(1.0, rng.lognormvariate(math.log(median * multiplier), sigma)), 2)


def _at(day: date, hour: int, rng: random.Random) -> datetime:
    return datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59))


def _legit_transaction(rng: random.Random, profile: CustomerProfile, day: date) -> dict:
    if rng.random() < 0.8:
        category = rng.choice(profile.favorite_categories)
    else:
        category = rng.choice(sorted(CATEGORIES))

    if rng.random() < LEGIT_NIGHT_PROB:
        hour = rng.randint(0, 5)
    else:
        hour = rng.randint(*profile.active_hours)

    amount = _amount(rng, category, profile.spend_multiplier)
    if rng.random() < LEGIT_BIG_PURCHASE_PROB:
        category = "electronics"
        amount = round(rng.uniform(1500, 7000), 2)

    return {
        "customer_id": profile.customer_id,
        "amount": amount,
        "merchant": rng.choice(CATEGORIES[category][0]),
        "category": category,
        "card_network": profile.card_network,
        "timestamp": _at(day, hour, rng),
        "is_fraud": 0,
    }


def _fraud_episode(rng: random.Random, profile: CustomerProfile, day: date) -> list[dict]:
    """Gera um episodio de fraude: card testing ou account takeover."""
    hour = rng.randint(0, 5) if rng.random() < 0.5 else rng.randint(6, 23)
    start = _at(day, hour, rng)

    def tx(ts: datetime, category: str, amount: float) -> dict:
        return {
            "customer_id": profile.customer_id,
            "amount": round(amount, 2),
            "merchant": rng.choice(CATEGORIES[category][0]),
            "category": category,
            "card_network": profile.card_network,
            "timestamp": ts,
            "is_fraud": 1,
        }

    if rng.random() < 0.5:
        # Card testing: varias compras pequenas em minutos, depois uma grande.
        txs, ts = [], start
        for _ in range(rng.randint(3, 6)):
            ts += timedelta(seconds=rng.randint(20, 240))
            txs.append(tx(ts, "shopping", rng.uniform(1, 15)))
        ts += timedelta(seconds=rng.randint(60, 600))
        txs.append(tx(ts, "electronics", rng.uniform(1500, 6000)))
        return txs

    # Account takeover: valores muito acima do perfil, fora das categorias usuais.
    unusual = [c for c in ("electronics", "shopping") if c not in profile.favorite_categories]
    category = rng.choice(unusual or ["electronics"])
    typical = CATEGORIES[category][1] * profile.spend_multiplier
    txs, ts = [], start
    for _ in range(rng.randint(1, 3)):
        ts += timedelta(minutes=rng.randint(1, 30))
        txs.append(tx(ts, category, typical * rng.uniform(3, 10)))
    return txs


def generate_transactions(
    day: date,
    customers: int = DEFAULT_CUSTOMERS,
    seed: int = DEFAULT_SEED,
) -> list[dict]:
    """Retorna as transacoes de um dia, ordenadas por horario. Deterministico."""
    transactions: list[dict] = []

    for index in range(1, customers + 1):
        profile = customer_profile(index, seed)
        rng = random.Random(f"day|{seed}|{day.isoformat()}|{profile.customer_id}")

        customer_txs = [
            _legit_transaction(rng, profile, day) for _ in range(_poisson(rng, profile.daily_rate))
        ]
        if rng.random() < FRAUD_EPISODE_PROB:
            customer_txs.extend(_fraud_episode(rng, profile, day))

        for sequence, tx in enumerate(customer_txs):
            # Episodios que cruzam a meia-noite ficam no dia gerado: corta no fim do dia.
            end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59)
            tx["timestamp"] = min(tx["timestamp"], end_of_day)
            tx["transaction_id"] = str(
                uuid.uuid5(ID_NAMESPACE, f"{seed}|{day.isoformat()}|{profile.customer_id}|{sequence}")
            )
            transactions.append(tx)

    transactions.sort(key=lambda t: (t["timestamp"], t["transaction_id"]))
    for tx in transactions:
        tx["timestamp"] = tx["timestamp"].isoformat()
    return transactions
