"""
Validation script for generated datasets.
Supports both ';' and ',' CSV delimiters, and '.' / ',' decimal separators.
"""
import csv
from datetime import datetime
from pathlib import Path


def get_csv_reader(f):
    """Detect delimiter (; or ,) from header and return DictReader."""
    first_line = f.readline()
    f.seek(0)
    delimiter = ";" if ";" in first_line else ","
    return csv.DictReader(f, delimiter=delimiter), delimiter


def validate():
    # 1. Validate apps.csv
    apps = {}
    with open("apps.csv", "r", encoding="utf-8") as f:
        reader, delim = get_csv_reader(f)
        for row in reader:
            aid = int(row["app_id"])
            assert aid > 0, f"Invalid app_id: {aid}"
            assert row["platform"] in ("Android", "iOS"), f"Invalid platform: {row['platform']}"
            assert int(row["store_id"]) > 0, f"Invalid store_id: {row['store_id']}"
            datetime.strptime(row["launched_on"], "%Y-%m-%d %H:%M:%S")
            apps[aid] = row

    print(f"[OK] apps.csv valid: {len(apps)} apps (delimiter: '{delim}')")

    # 2. Validate campaign_costs.csv
    costs_cnt = 0
    cost_sep_detected = set()
    with open("campaign_costs.csv", "r", encoding="utf-8") as f:
        reader, delim = get_csv_reader(f)
        for row in reader:
            costs_cnt += 1
            aid = int(row["app_id"])
            assert aid in apps, f"app_id {aid} not found in apps.csv"

            cost_str = row["cost_usd"]
            if "," in cost_str:
                cost_sep_detected.add(",")
            elif "." in cost_str:
                cost_sep_detected.add(".")

            cost = float(cost_str.replace(",", "."))
            assert cost >= 0, f"Invalid cost: {cost}"
            imp = int(row["impressions"])
            clicks = int(row["clicks"])
            assert imp > 0 and clicks > 0, f"Invalid impressions/clicks: {imp}, {clicks}"
            assert clicks <= imp, f"clicks {clicks} > impressions {imp}"
            datetime.strptime(row["date"], "%Y-%m-%d %H:%M:%S")

    sep_display = ", ".join(repr(s) for s in (cost_sep_detected or {"."}))
    print(f"[OK] campaign_costs.csv valid: {costs_cnt} rows (delimiter: '{delim}', decimal sep: {sep_display})")

    # 3. Validate events_raw.csv
    events_cnt = 0
    dirty_country = 0
    dirty_revenue = 0
    multi_day_latency_cnt = 0
    max_latency_hours = 0.0

    events_by_id = {}
    duplicate_events_cnt = 0
    diff_ingested_cnt = 0
    diff_revenue_cnt = 0
    rev_sep_detected = set()

    with open("events_raw.csv", "r", encoding="utf-8") as f:
        reader, delim = get_csv_reader(f)
        for row in reader:
            events_cnt += 1
            eid = int(row["event_id"])
            assert eid > 0
            aid = int(row["app_id"])
            assert aid in apps, f"app_id {aid} not in apps"
            assert len(row["event_name"]) <= 20, f"event_name too long: {row['event_name']}"

            t_event = datetime.strptime(row["event_time"], "%Y-%m-%d %H:%M:%S")
            t_ingest = datetime.strptime(row["ingested_at"], "%Y-%m-%d %H:%M:%S")
            assert t_ingest >= t_event, f"ingested_at {t_ingest} < event_time {t_event}"

            diff_seconds = (t_ingest - t_event).total_seconds()
            diff_hours = diff_seconds / 3600.0
            if diff_hours > max_latency_hours:
                max_latency_hours = diff_hours
            if diff_seconds >= 86400:
                multi_day_latency_cnt += 1

            assert row["is_test"] in ("true", "false"), f"Invalid is_test: {row['is_test']}"

            c = row["country"]
            if c in ("", "--") or c.islower() or len(c) != 2:
                dirty_country += 1

            rev = row["revenue_usd"]
            if rev in ("", "NULL", "null", "N/A"):
                dirty_revenue += 1
            else:
                if "," in rev:
                    rev_sep_detected.add(",")
                elif "." in rev:
                    rev_sep_detected.add(".")
                val = float(rev.replace(",", "."))
                assert val >= 0, f"Negative revenue: {rev}"

            # Duplicate event_id check
            if eid in events_by_id:
                duplicate_events_cnt += 1
                prev_row = events_by_id[eid]
                assert row["ingested_at"] != prev_row["ingested_at"], (
                    f"Duplicate event {eid} has identical ingested_at: {row['ingested_at']}"
                )
                diff_ingested_cnt += 1
                if row["revenue_usd"] != prev_row["revenue_usd"]:
                    diff_revenue_cnt += 1
            else:
                events_by_id[eid] = row

    rev_sep_disp = ", ".join(repr(s) for s in (rev_sep_detected or {"."}))
    print(f"[OK] events_raw.csv valid: {events_cnt} rows ({len(events_by_id)} unique event_id, delimiter: '{delim}', decimal sep: {rev_sep_disp})")
    print(f"     Dirty country          : {dirty_country} ({dirty_country / events_cnt * 100:.2f}%)")
    print(f"     Dirty revenue          : {dirty_revenue} ({dirty_revenue / events_cnt * 100:.2f}%)")
    print(f"     Multi-day delay (>=24h): {multi_day_latency_cnt} ({multi_day_latency_cnt / events_cnt * 100:.2f}%)")
    print(f"     Max latency observed   : {max_latency_hours:.1f} hours ({max_latency_hours / 24:.1f} days)")
    print(f"     Duplicate event_id rows: {duplicate_events_cnt} ({duplicate_events_cnt / events_cnt * 100:.2f}%)")
    print(f"       - with different ingested_at: {diff_ingested_cnt} (100.0%)")
    print(f"       - with updated revenue_usd  : {diff_revenue_cnt} ({diff_revenue_cnt / duplicate_events_cnt * 100:.1f}%)" if duplicate_events_cnt else "")
    print("\n[SUCCESS] All data validation checks passed perfectly!")


if __name__ == "__main__":
    validate()
