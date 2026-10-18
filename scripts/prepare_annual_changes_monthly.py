"""Repeat annual percentage-point changes on the reference monthly calendar.

Run with: python scripts/prepare_annual_changes_monthly.py

The annual source label YYYY0101 represents statistical year YYYY - 1.
Source labels after 2027-01-01 are excluded, retaining statistical 2026.
Changes are current minus previous annual ratios, in percentage points;
there is no logarithm, multiplication by 100, or division by 12.
Each change is repeated in every reference month of its statistical year.
2011 levels supply the lag needed for the first year, 2012.

This is alignment by statistical year, not by publication/availability date.
The source period_classification is retained: statistical 2026 uses a
projection. Source files and existing final datasets remain unchanged.
"""

import csv
import json
from datetime import date, datetime
from decimal import Decimal

from prepare_trade_monthly import FINAL, ROOT, read_csv, reference_dates


SOURCE_LABEL_CUTOFF = date(2027, 1, 1)
SERIES = (
    (
        "5. IMF_general_government_gross_debt_percent_gdp.csv",
        "general_government_gross_debt",
    ),
    (
        "6. IMF_current_account_balance_percent_gdp.csv",
        "current_account_balance",
    ),
)


def prepare_series(filename, series, dates):
    source_column = f"{series}_percent_gdp"
    value_column = f"{series}_annual_change_pp"
    annual = {}
    excluded = []
    for row in read_csv(ROOT / "data" / "cleaned" / filename):
        label = datetime.strptime(row["date"], "%Y%m%d").date()
        if (label.month, label.day) != (1, 1):
            raise ValueError(f"Unexpected annual label in {filename}: {label}")
        if label > SOURCE_LABEL_CUTOFF:
            excluded.append(label.isoformat())
            continue
        year = label.year - 1
        if year in annual:
            raise ValueError(f"Duplicate statistical year in {filename}: {year}")
        value = Decimal(row[source_column])
        if not value.is_finite():
            raise ValueError(f"Nonfinite annual value in {filename}: {year}")
        annual[year] = (value, row["period_classification"])

    changes = {}
    for year in sorted({date.fromisoformat(timestamp).year for timestamp in dates}):
        if year not in annual or year - 1 not in annual:
            raise ValueError(f"Missing annual value or lag for {series}: {year}")
        changes[year] = annual[year][0] - annual[year - 1][0]

    output = []
    for timestamp in dates:
        year = date.fromisoformat(timestamp).year
        output.append({
            "date": timestamp,
            value_column: format(changes[year], "f"),
            "period_classification": annual[year][1],
        })

    path = FINAL / f"{series}_annual_change_pp_monthly.csv"
    summary = {
        "file": path.name,
        "rows": len(output),
        "start": dates[0],
        "end": dates[-1],
        "excluded_source_labels": excluded,
        "annual_changes_pp": {year: format(value, "f") for year, value in changes.items()},
        "projection_months": sum(
            row["period_classification"].startswith("Projection") for row in output
        ),
    }
    return path, ["date", value_column, "period_classification"], output, summary


def main():
    dates = reference_dates()
    prepared = [prepare_series(filename, series, dates) for filename, series in SERIES]
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
