from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pandas as pd

from pipeline.task_3_1_clean import clean_events


def parse_args() -> argparse.Namespace:
    """ Parse command line arguments. """
    parser = argparse.ArgumentParser(description="Clean and process raw event data.")

    parser.add_argument("--input", type=Path, required=True,
                        help="Directory containing events_raw.csv.", )

    parser.add_argument("--output", type=Path, required=True,
                        help="Directory for pipeline output.", )

    parser.add_argument("--since", type=str, required=True,
                        help="Keep events with ingested_at >= this timestamp.", )

    return parser.parse_args()


def read_events(input_dir: Path) -> pd.DataFrame:
    """ Read raw events from CSV. """
    input_file = input_dir / "events_raw.csv"

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    raw_events_df = pd.read_csv(
        input_file,
        sep=";",
        dtype=str,
        keep_default_na=False)

    print("COLUMNS:", raw_events_df.columns.tolist())
    return raw_events_df


def deduplicate_events(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """ Keep the latest ingested_at record for each event_id. """
    if df.empty:
        return df.copy(), 0

    len_df_before = len(df)

    # Sort the dataframe according to a specified rule.
    sorted_df = df.sort_values(
        by=["event_id", "ingested_at"],
        ascending=[True, False],
        kind="stable")

    # Discard duplicates, keeping the last record for each event_id.
    result_df = sorted_df.drop_duplicates(
        subset=["event_id"],
        keep="first")

    # Rebuilding the dataframe index again
    result_df = result_df.reset_index(drop=True)

    return result_df, len_df_before - len(result_df)


def filter_since(df: pd.DataFrame, since: str) -> pd.DataFrame:
    """ Keep events ingested at or after the requested timestamp. """
    since_timestamp = pd.to_datetime(
        since,
        utc=True,
        errors="raise")

    if df.empty:
        return df.copy()

    return df.loc[df["ingested_at"] >= since_timestamp].reset_index(drop=True)


def write_quarantine(quarantine_df: pd.DataFrame, output_dir: Path) -> None:
    """ Writing a data frame with invalid events """
    quarantine_dir = output_dir / "quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    quarantine_file = quarantine_dir / "quarantine_events.csv"
    quarantine_df.to_csv(quarantine_file, index=False)


def write_clean_events(clean_df: pd.DataFrame, output_dir: Path) -> None:
    """ Write clean events to partitioned Parquet. """
    clean_dir = output_dir / "clean_events"
    clean_dir.mkdir(parents=True, exist_ok=True)

    # Creating a date column for partitioning
    clean_df["event_date"] = clean_df["event_time"].dt.date

    # Parquet output
    clean_df.to_parquet(
        clean_dir,
        engine="pyarrow",
        partition_cols=["event_date"],
        index=False)


def print_summary(stats: Counter) -> None:
    print(
        f"input={stats['input_rows']} "
        f"clean={stats['clean_rows']} "
        f"output={stats['output_rows']} "
        f"duplicates={stats['duplicates_removed']} "
        f"quarantine={stats['quarantine_rows']} "
        f"test={stats['test_rows']} "
        f"invalid_revenue={stats['invalid_revenue']} "
        f"invalid_country={stats['invalid_country']} "
        f"invalid_event_time={stats['invalid_event_time']} "
        f"invalid_ingested_at={stats['invalid_ingested_at']}")


def main() -> None:
    args = parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    # Read the complete raw dataset.
    input_df = read_events(args.input)

    # Clean and validate the complete dataset.
    clean_df, quarantine_df, stats = clean_events(input_df)

    # Deduplicate after cleaning.
    clean_df, duplicates_removed = deduplicate_events(clean_df)
    stats["duplicates_removed"] = duplicates_removed

    # Apply --since after deduplication.
    clean_df = filter_since(clean_df, args.since)
    stats["output_rows"] = len(clean_df)

    # Write clean events and quarantine datasets.
    write_clean_events(clean_df, args.output)
    write_quarantine(quarantine_df, args.output)

    # Print statistics
    print_summary(stats)


if __name__ == "__main__":
    main()
