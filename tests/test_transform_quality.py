from datetime import date

import pytest

from pipeline.quality import DataQualityError, enforce, run_checks
from pipeline.transform import SchemaError, normalize
from source_api.generator import generate_transactions

DAY = date(2026, 10, 1)


def _records():
    return generate_transactions(DAY, customers=30)


def test_normalize_types_and_dedup():
    records = _records()
    df = normalize(records + [records[0]])  # reenvio da mesma transacao
    assert len(df) == len(records)
    assert df["event_date"].eq(DAY).all()
    assert str(df["amount"].dtype) == "float64"


def test_normalize_missing_field_raises():
    records = _records()
    del records[0]["amount"]
    for r in records:
        r.pop("amount", None)
    with pytest.raises(SchemaError):
        normalize(records)


def test_valid_day_passes_all_checks():
    enforce(run_checks(normalize(_records()), DAY))


@pytest.mark.parametrize(
    ("field", "value", "check"),
    [
        ("amount", -10, "amount_positive"),
        ("amount", None, "no_nulls"),
        ("timestamp", "2026-09-30T10:00:00", "event_date_matches_batch"),
        ("is_fraud", 7, "is_fraud_binary"),
    ],
)
def test_bad_records_are_rejected(field, value, check):
    records = _records()
    records[0][field] = value
    with pytest.raises(DataQualityError) as exc:
        enforce(run_checks(normalize(records), DAY))
    assert check in {f.name for f in exc.value.failures}


def test_empty_day_is_rejected():
    with pytest.raises(DataQualityError):
        enforce(run_checks(normalize([]), DAY))
