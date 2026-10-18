"""Align three trade log-change series to USDSLE_monthly.csv.

Run from any directory with: python scripts/prepare_trade_monthly.py

The cleaned trade files label each statistical month with the first day of
the following month. Subtract one day to obtain the matching month-end.
Use December 2011 levels to calculate January 2012 changes before selecting
the final sample. Existing source imputations are retained; no new filling
is performed. A missing or nonpositive current/previous level yields an
empty CSV field, while the date row is retained.

The fuel_imports output uses mineral fuels and lubricants imports as its
source series, replacing the narrower fuel imports series.
"""

import calendar
import csv
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data" / "final_monthly"
SERIES = (
    (
        "3. SLE_Trade_RawMonthly_mineral_fuels_lubricants_imports_usd_thousands.csv",
        "mineral_fuels_lubricants_imports_usd_thousands",
        "fuel_imports",
    ),
    (
        "4. SLE_Trade_RawMonthly_food_imports_usd_thousands.csv",
        "food_imports_usd_thousands",
        "food_imports",
    ),
    (
        "7. SLE_Trade_RawMonthly_iron_ore_exports_usd_thousands.csv",
        "iron_ore_exports_usd_thousands",
        "iron_ore_exports",
    ),
)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def reference_dates():
    dates = [row["date"] for row in read_csv(FINAL / "USDSLE_monthly.csv")]
    expected = [
        date(year, month, calendar.monthrange(year, month)[1]).isoformat()
        for year in range(2012, 2027)
        for month in range(1, 13)
        if (year, month) <= (2026, 6)
    ]
    if dates != expected:
        raise ValueError("USDSLE reference must contain all 174 month-ends in order.")
    return dates


def prepare_series(filename, column, series, dates):
    levels = {}
    filled = {}
    for row in read_csv(ROOT / "data" / "cleaned" / filename):
        label = datetime.strptime(row["date"], "%Y%m%d").date()
        if label.day != 1:
            raise ValueError(f"Unexpected source label in {filename}: {label}")
        month_end = (label - timedelta(days=1)).isoformat()
        if month_end in levels:
            raise ValueError(f"Duplicate month in {filename}: {month_end}")
        value = float(row[column]) if row[column].strip() else None
        if value is not None and not math.isfinite(value):
            raise ValueError(f"Nonfinite source value in {filename}: {month_end}")
        levels[month_end] = value
        filled[month_end] = row["is_forward_filled"].lower() == "true"

    output = []
    missing_dates = []
    for timestamp in dates:
        month_end = date.fromisoformat(timestamp)
        previous_end = (month_end.replace(day=1) - timedelta(days=1)).isoformat()
        if timestamp not in levels or previous_end not in levels:
            raise ValueError(f"Missing source month for {series}: {timestamp}")
        current, previous = levels[timestamp], levels[previous_end]
        if current is None or previous is None or current <= 0 or previous <= 0:
            result = ""
            missing_dates.append(timestamp)
        else:
            change = 100 * (math.log(current) - math.log(previous))
            result = f"{change:.12f}".rstrip("0").rstrip(".")
        output.append((timestamp, result))

    path = FINAL / f"{series}_log_change_monthly.csv"
    summary = {
        "file": path.name,
        "rows": len(output),
        "valid_changes": len(output) - len(missing_dates),
        "missing_change_dates": missing_dates,
        "source_forward_filled_months": sum(filled[timestamp] for timestamp in dates),
    }
    return path, f"{series}_log_change_pct", output, summary


def main():
    dates = reference_dates()
    prepared = [
        prepare_series(filename, column, series, dates)
        for filename, column, series in SERIES
    ]
    for path, column, rows, summary in prepared:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(("date", column))
            writer.writerows(rows)
        saved = read_csv(path)
        if [row["date"] for row in saved] != dates:
            raise ValueError(f"Output dates do not match the reference: {path}")
        print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
