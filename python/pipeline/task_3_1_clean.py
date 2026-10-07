from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd


def normalize_revenue(value: str, stats: Counter) -> Decimal:
    """ Normalize revenue_usd to Decimal with two decimal places. """
    value = value.strip()

    if not value or value.upper() == "NULL":
        stats["invalid_revenue"] += 1
        return Decimal("0.00")

    value = value.replace(",", ".")
    try:
        revenue = Decimal(value)
        if not revenue.is_finite():
            raise InvalidOperation
        return revenue.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    except (InvalidOperation, ValueError):
        stats["invalid_revenue"] += 1
        return Decimal("0.00")


def normalize_country(value: str, stats: Counter) -> str:
    """ Normalize country to two uppercase letters or XX. """
    value = value.strip()

    if len(value) == 2 and value.isalpha():
        return value.upper()

    stats["invalid_country"] += 1
    return "XX"


def normalize_timestamp(value: str) -> pd.Timestamp | None:
    """ Convert timestamp to timezone-aware UTC datetime. """
    value = value.strip()

    if not value:
        return None

    try:
        return pd.to_datetime(
            value,
            utc=True,
            errors="raise",
        )
    except (TypeError, ValueError):
        return None


def clean_events(df: pd.DataFrame, ) -> tuple[pd.DataFrame, pd.DataFrame, Counter]:
    """
    Clean and validate the complete input dataset.

    Returns:
        clean_df: normalized, valid, non-test events.
        quarantine_df: rows with critical validation errors.
        stats: processing statistics.
    """
    stats = Counter()
    stats["input_rows"] = len(df)

    clean_records = []
    quarantine_records = []

    for row in df.itertuples(index=False):
        record = row._asdict()
        invalid_fields = []

        # Critical fields checking.
        if not record["event_id"].strip():
            invalid_fields.append("event_id")

        if not record["app_id"].strip():
            invalid_fields.append("app_id")

        # Normalize revenue and country.
        record["revenue_usd"] = normalize_revenue(record["revenue_usd"], stats)
        record["country"] = normalize_country(record["country"], stats)

        # Normalize timestamp fields.
        record["event_time"] = normalize_timestamp(record["event_time"])
        record["ingested_at"] = normalize_timestamp(record["ingested_at"])

        if record["event_time"] is None:
            invalid_fields.append("event_time")
            stats["invalid_event_time"] += 1

        if record["ingested_at"] is None:
            invalid_fields.append("ingested_at")
            stats["invalid_ingested_at"] += 1

        # Normalize test flag.
        is_test = record["is_test"].strip().lower() == "true"
        record["is_test"] = is_test

        # Exclude test traffic.
        if is_test:
            stats["test_rows"] += 1
            continue

        # Invalid rows put to quarantine.
        if invalid_fields:
            record["invalid_fields"] = ",".join(invalid_fields)
            quarantine_records.append(record)
            stats["quarantine_rows"] += 1
            continue

        clean_records.append(record)

    clean_df = pd.DataFrame(clean_records)
    quarantine_df = pd.DataFrame(quarantine_records)

    stats["clean_rows"] = len(clean_df)

    return clean_df, quarantine_df, stats
