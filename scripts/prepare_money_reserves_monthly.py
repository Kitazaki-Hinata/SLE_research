"""Align base-money and FX-reserve log changes to the monthly FX calendar.

Run with: python scripts/prepare_money_reserves_monthly.py

These two sources use first-of-SAME-month labels, unlike the trade files.
Map each label to that month's last day. Compute 100 * (ln E_t - ln E_t-1)
using consecutive calendar months, retaining December 2011 as the lag for
January 2012. Missing or nonpositive levels in either month produce an
empty field, without filling or forecasting. All 174 reference rows remain.
Reserve values use the USD millions column; the USD column is the same
series in a different scale and does not require a second output.
"""

import calendar
import csv
import json
import math
from datetime import date, datetime, timedelta

from prepare_trade_monthly import FINAL, ROOT, read_csv, reference_dates


SERIES = (
    (
        "1. Base_Money_monthly_values_updated.csv",
        "monetary_base_million_local_currency",
        "base_money",
    ),
    (
        "2. FX_Reserves_monthly_values_updated.csv",
        "reserves_usd_millions",
        "fx_reserves",
    ),
)


def prepare_series(filename, source_column, series, dates):
    levels = {}
    for row in read_csv(ROOT / "data" / "cleaned" / filename):
        label = datetime.strptime(row["date"], "%Y%m%d").date()
        if label.day != 1:
            raise ValueError(f"Unexpected source label in {filename}: {label}")
        timestamp = label.replace(day=calendar.monthrange(label.year, label.month)[1]).isoformat()
        if timestamp in levels:
            raise ValueError(f"Duplicate source month in {filename}: {timestamp}")
        raw_value = row[source_column].strip()
        value = float(raw_value) if raw_value else None
        if value is not None and not math.isfinite(value):
            raise ValueError(f"Nonfinite source value in {filename}: {timestamp}")
        levels[timestamp] = value

    value_column = f"{series}_log_change_pct"
    output = []
    missing_dates = []
    for timestamp in dates:
        previous_timestamp = (
            date.fromisoformat(timestamp).replace(day=1) - timedelta(days=1)
        ).isoformat()
        current = levels.get(timestamp)
        previous = levels.get(previous_timestamp)
        if current is None or previous is None or current <= 0 or previous <= 0:
            result = ""
            missing_dates.append(timestamp)
        else:
            change = 100 * (math.log(current) - math.log(previous))
            result = f"{change:.12f}".rstrip("0").rstrip(".")
        output.append({"date": timestamp, value_column: result})

    path = FINAL / f"{series}_log_change_monthly.csv"
    summary = {
        "file": path.name,
        "rows": len(output),
        "start": dates[0],
        "end": dates[-1],
        "valid_changes": len(output) - len(missing_dates),
        "missing_change_dates": missing_dates,
    }
    return path, ["date", value_column], output, summary


def main():
    dates = reference_dates()
    prepared = [
        prepare_series(filename, column, series, dates)
        for filename, column, series in SERIES
    ]
    for path, columns, rows, summary in prepared:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        if read_csv(path) != rows:
            raise ValueError(f"Written output does not match prepared data: {path}")
        print(json.dumps(summary))


if __name__ == "__main__":
    main()
