"""Checagens de qualidade executadas antes de os dados chegarem na staging.

Se qualquer checagem bloqueante falhar, o dia inteiro e rejeitado: e melhor um
dia faltando (visivel, alertavel) do que um dia com dados errados no mart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

REQUIRED_NOT_NULL = [
    "transaction_id",
    "customer_id",
    "amount",
    "merchant",
    "category",
    "card_network",
    "event_ts",
    "is_fraud",
]
MAX_AMOUNT = 100_000.0
MAX_FRAUD_RATE = 0.10


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


class DataQualityError(Exception):
    def __init__(self, failures: list[CheckResult]):
        self.failures = failures
        summary = "; ".join(f"{f.name}: {f.detail}" for f in failures)
        super().__init__(f"{len(failures)} checagem(ns) falharam -> {summary}")


def run_checks(df: pd.DataFrame, day: date) -> list[CheckResult]:
    results: list[CheckResult] = []

    def check(name: str, failing: int, detail: str) -> None:
        results.append(CheckResult(name, failing == 0, detail if failing else "ok"))

    check("not_empty", int(df.empty), "nenhuma transacao para o dia")
    if df.empty:
        return results

    nulls = df[REQUIRED_NOT_NULL].isna().sum()
    nulls = nulls[nulls > 0]
    check("no_nulls", int(nulls.sum()), f"nulos por coluna: {nulls.to_dict()}")

    dup = int(df["transaction_id"].duplicated().sum())
    check("unique_transaction_id", dup, f"{dup} ids duplicados")

    non_positive = int((df["amount"] <= 0).sum())
    check("amount_positive", non_positive, f"{non_positive} valores <= 0")

    too_high = int((df["amount"] > MAX_AMOUNT).sum())
    check("amount_upper_bound", too_high, f"{too_high} valores acima de {MAX_AMOUNT:,.0f}")

    outside = int((df["event_date"] != day).sum())
    check("event_date_matches_batch", outside, f"{outside} transacoes fora de {day}")

    bad_label = int((~df["is_fraud"].isin([0, 1])).sum())
    check("is_fraud_binary", bad_label, f"{bad_label} rotulos fora de 0/1")

    fraud_rate = float(df["is_fraud"].fillna(0).mean())
    check(
        "fraud_rate_plausible",
        int(fraud_rate > MAX_FRAUD_RATE),
        f"taxa de fraude {fraud_rate:.1%} acima de {MAX_FRAUD_RATE:.0%}",
    )
    return results


def enforce(results: list[CheckResult]) -> None:
    failures = [r for r in results if not r.passed]
    if failures:
        raise DataQualityError(failures)
