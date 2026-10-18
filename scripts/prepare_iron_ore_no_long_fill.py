"""Create an iron ore log-change variant excluding two long forward-fill runs.

Run with: python scripts/prepare_iron_ore_no_long_fill.py

The excluded statistical months are June 2018-June 2019 and August
2019-December 2020. Source labels are the first day of the following month.
If the current or previous month's level was filled in either interval,
the log change is left empty. This also excludes July 2019 and January 2021
changes. Earlier forward fills remain as in the original log-change file.
All 174 reference dates are retained. Neither the cleaned source nor the
original log-change file is modified.
"""

import csv
import json
from datetime import date, datetime, timedelta

from prepare_trade_monthly import FINAL, ROOT, read_csv, reference_dates


SOURCE = ROOT / "data/cleaned/7. SLE_Trade_RawMonthly_iron_ore_exports_usd_thousands.csv"
ORIGINAL = FINAL / "iron_ore_exports_log_change_monthly.csv"
OUTPUT = FINAL / "iron_ore_exports_log_change_monthly_no_long_fill.csv"
EXCLUDED_PERIODS = (("2018-06", "2019-06"), ("2019-08", "2020-12"))
VALUE_COLUMN = "iron_ore_exports_log_change_pct"


def main():
    dates = reference_dates()
    original = read_csv(ORIGINAL)
    if [row["date"] for row in original] != dates:
        raise ValueError("Original iron ore dates must match USDSLE_monthly.csv.")

    source_dates = set()
    excluded_dates = set()
    for row in read_csv(SOURCE):
        label = datetime.strptime(row["date"], "%Y%m%d").date()
        if label.day != 1:
            raise ValueError(f"Unexpected source label: {label}")
        timestamp = (label - timedelta(days=1)).isoformat()
        if timestamp in source_dates:
            raise ValueError(f"Duplicate source month: {timestamp}")
        source_dates.add(timestamp)
        in_long_gap = any(start <= timestamp[:7] <= end for start, end in EXCLUDED_PERIODS)
        if in_long_gap and row["is_forward_filled"].lower() == "true":
            excluded_dates.add(timestamp)

    output = []
    affected_dates = []
    for row in original:
        timestamp = row["date"]
        previous = (date.fromisoformat(timestamp).replace(day=1) - timedelta(days=1)).isoformat()
        if timestamp not in source_dates or previous not in source_dates:
            raise ValueError(f"Missing source month for {timestamp}")
        result = dict(row)
        if timestamp in excluded_dates or previous in excluded_dates:
            result[VALUE_COLUMN] = ""
            affected_dates.append(timestamp)
        output.append(result)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", VALUE_COLUMN], lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)

    print(json.dumps({
        "file": OUTPUT.name,
        "rows": len(output),
        "excluded_filled_level_months": len(excluded_dates),
        "excluded_change_dates": affected_dates,
        "valid_changes": sum(bool(row[VALUE_COLUMN]) for row in output),
    }))


if __name__ == "__main__":
    main()
