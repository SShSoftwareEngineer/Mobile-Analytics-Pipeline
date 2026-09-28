from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from pipeline.clean import clean_events


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean and process raw event data."
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Directory containing events_raw.csv.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory for pipeline output.",
    )

    parser.add_argument(
        "--since",
        type=str,
        required=True,
        help="Process records with ingested_at >= this date/time.",
    )

    return parser.parse_args()


def read_events(input_dir: Path) -> pd.DataFrame:
    input_file = input_dir / "events_raw.csv"

    if not input_file.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_file}"
        )

    return pd.read_csv(
        input_file,
        dtype=str,
        keep_default_na=False,
    )

def write_quarantine(
    quarantine_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    quarantine_dir = output_dir / "quarantine"
    quarantine_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    quarantine_file = quarantine_dir / "events.csv"

    quarantine_df.to_csv(
        quarantine_file,
        index=False,
    )


def write_clean_events(
    clean_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    clean_dir = output_dir / "clean_events"
    clean_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Temporary implementation.
    # Parquet partitioning and safe replacement will be added
    # after we verify the Decimal -> Parquet behavior.
    clean_file = clean_dir / "events.parquet"

    clean_df.to_parquet(
        clean_file,
        engine="pyarrow",
        index=False,
    )


def print_summary(stats) -> None:
    print(
        "input={input_rows} "
        "output={output_rows} "
        "duplicates={duplicates_removed} "
        "quarantine={quarantine_rows}".format(
            input_rows=stats["input_rows"],
            output_rows=stats["output_rows"],
            duplicates_removed=stats["duplicates_removed"],
            quarantine_rows=stats["quarantine_rows"],
        )
    )


def main() -> None:
    args = parse_args()

    args.output.mkdir(
        parents=True,
        exist_ok=True,
    )

    input_df = read_events(
        args.input,
        args.since,
    )

    clean_df, quarantine_df, stats = clean_events(
        input_df,
    )

    write_clean_events(
        clean_df,
        args.output,
    )

    write_quarantine(
        quarantine_df,
        args.output,
    )

    print_summary(stats)


if __name__ == "__main__":
    main()