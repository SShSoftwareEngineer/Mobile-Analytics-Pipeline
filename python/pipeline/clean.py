from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import pandas as pd


MONEY_QUANT = Decimal("0.01")


def normalize_revenue(value: str, stats: Counter) -> Decimal:
    """Normalize revenue_usd to Decimal with two decimal places."""
    value = value.strip()

    if not value or value.upper() == "NULL":
        stats["invalid_revenue"] += 1
        return Decimal("0.00")

    value = value.replace(",", ".")

    try:
        revenue = Decimal(value)
    except InvalidOperation:
        stats["invalid_revenue"] += 1
        return Decimal("0.00")

    return revenue.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def normalize_country(value: str, stats: Counter) -> str:
    """Normalize country to two uppercase letters or XX."""
    value = value.strip()

    if len(value) == 2 and value.isalpha():
        return value.upper()

    stats["invalid_country"] += 1
    return "XX"


def normalize_timestamp(value: str) -> pd.Timestamp | None:
    """Convert a UTC timestamp to a timezone-aware UTC datetime."""
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


def clean_events(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, Counter]:
    """
    Clean, validate, quarantine and deduplicate event data.

    Returns:
        clean_df: normalized, non-test, deduplicated events.
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

        # Critical fields.
        if not record["event_id"].strip():
            invalid_fields.append("event_id")

        if not record["app_id"].strip():
            invalid_fields.append("app_id")

        # Normalize revenue and country.
        record["revenue_usd"] = normalize_revenue(
            record["revenue_usd"],
            stats,
        )

        record["country"] = normalize_country(
            record["country"],
            stats,
        )

        # Normalize timestamps.
        record["event_time"] = normalize_timestamp(
            record["event_time"],
        )

        record["ingested_at"] = normalize_timestamp(
            record["ingested_at"],
        )

        if record["event_time"] is None:
            invalid_fields.append("event_time")

        if record["ingested_at"] is None:
            invalid_fields.append("ingested_at")

        # Normalize test flag.
        is_test = record["is_test"].strip().lower() == "true"
        record["is_test"] = is_test

        # Test traffic is excluded, but is not considered invalid.
        if is_test:
            stats["test_rows"] += 1
            continue

        # Invalid rows go to quarantine.
        if invalid_fields:
            record["invalid_fields"] = ",".join(invalid_fields)
            quarantine_records.append(record)
            stats["quarantine_rows"] += 1
            continue

        clean_records.append(record)

    # Deduplicate by event_id, keeping the latest ingested_at.
    clean_df = pd.DataFrame(clean_records)

    if not clean_df.empty:
        clean_df = (
            clean_df
            .sort_values(
                ["event_id", "ingested_at"],
                ascending=[True, False],
                kind="stable",
            )
            .drop_duplicates(
                subset="event_id",
                keep="first",
            )
            .reset_index(drop=True)
        )

    stats["duplicates_removed"] = len(clean_records) - len(clean_df)
    stats["output_rows"] = len(clean_df)

    quarantine_df = pd.DataFrame(quarantine_records)

    return clean_df, quarantine_df, stats