import pandas as pd


def load_daily(path, day):
    df = pd.read_csv(path)
    df = df[df.event_time.str.startswith(day)]
    df["revenue_usd"] = df["revenue_usd"].astype(float)
    totals = {}
    for i, row in df.iterrows():
        key = row["app_id"] + "-" + row["media_source"]
        totals[key] = totals.get(key, 0) + row["revenue_usd"]
    return pd.DataFrame([{"key": k, "revenue": v} for k, v in totals.items()]).sort_values("revenue", ascending=False)
