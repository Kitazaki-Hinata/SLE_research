"""Align existing monthly factors to the POS FX calendar by availability date.

Run: python scripts/prepare_pos_daily_factors.py
Check existing outputs without writing: python scripts/prepare_pos_daily_factors.py --check

Publication evidence lives in data/3_POS_prediction_daily/metadata/. Missing
publication dates use the user's next-month-15 / next-year-June-18 convention.
Values retain their original economic frequency, units, and decimal strings.
This is date alignment of the supplied vintage, not a historical-vintage rebuild.
"""

import argparse
import bisect
import calendar
import csv
import hashlib
import io
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/2_regression_monthly"
OUTPUT = ROOT / "data/3_POS_prediction_daily"
META = OUTPUT / "metadata"
REFERENCE = OUTPUT / "USDSLE_daily.csv"
FACTORS = {
    "headline_cpi_log_change_monthly": ("monthly", "cpi_release_evidence.csv"),
    "fx_reserves_log_change_monthly": ("monthly", "reserves_release_evidence.csv"),
    "gdp_annual_pct_change_monthly": ("annual", "annual_release_evidence.csv"),
    "trade_balance_annual_pct_change_monthly": ("annual", "annual_release_evidence.csv"),
    "general_government_gross_debt_annual_change_pp_monthly": (
        "annual", "annual_release_evidence.csv"
    ),
}
EVENT_STEM = "Sierra_Leone_Policy_Event_Dummies"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def parse_date(value):
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date: {value!r}")


def csv_text(columns, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_observations(factor, frequency):
    columns, rows = read_csv(SOURCE / f"{factor}.csv")
    observations = {}
    for row in rows:
        raw = row[factor].strip()
        if not raw:
            continue
        if not Decimal(raw).is_finite():
            raise ValueError(f"Nonfinite {factor}: {row}")
        timestamp = parse_date(row["date"])
        period = timestamp.strftime("%Y-%m" if frequency == "monthly" else "%Y")
        classification = row.get("period_classification", "")
        if period in observations:
            previous = observations[period]
            if (Decimal(previous["value"]) != Decimal(raw)
                    or previous["period_classification"] != classification):
                raise ValueError(f"Inconsistent repeated annual value: {factor}, {period}")
        else:
            observations[period] = {
                "value": raw, "period_classification": classification,
            }
    return columns, observations


def evidence_for(factor, filename):
    _, rows = read_csv(META / filename)
    result = {}
    for row in rows:
        if row.get("factor", factor) != factor:
            continue
        period = row["period"]
        if period in result:
            raise ValueError(f"Duplicate release evidence: {factor}, {period}")
        result[period] = row
    return result


def period_end(period):
    if len(period) == 4:
        return date(int(period), 12, 31)
    year, month = map(int, period.split("-"))
    return date(year, month, calendar.monthrange(year, month)[1])


def assumed_release(period):
    if len(period) == 4:
        return date(int(period) + 1, 6, 18)
    year, month = map(int, period.split("-"))
    return date(year + (month == 12), month % 12 + 1, 15)


def prepare_factor(factor, frequency, evidence_file, labels, dates):
    input_columns, observations = source_observations(factor, frequency)
    evidence = evidence_for(factor, evidence_file)
    missing_evidence = set(observations) - set(evidence)
    if missing_evidence:
        raise ValueError(f"Missing researched periods for {factor}: {sorted(missing_evidence)}")
    records = []
    releases = {}
    for period in observations:
        raw_date = evidence[period].get("release_date", "").strip()
        releases[period] = parse_date(raw_date) if raw_date else assumed_release(period)
    for period, observation in observations.items():
        item = evidence[period]
        actual = bool(item.get("release_date", "").strip())
        released = releases[period]
        if frequency == "monthly" and released < period_end(period):
            raise ValueError(f"Monthly release precedes its statistical period end: {factor}, {period}")
        available = released
        position = bisect.bisect_left(dates, available)
        aligned = labels[position] if position < len(dates) else ""
        records.append({
            "factor": factor, "source_frequency": frequency, "source_period": period,
            "value": observation["value"],
            "period_classification": observation["period_classification"],
            "release_date": released.isoformat(), "available_date": available.isoformat(),
            "first_eligible_date": aligned,
            "date_basis": ("official_vintage_release" if item.get("confidence") == "identified_vintage_release"
                           else "official_period_release") if actual else (
                "assumed_next_month_15" if frequency == "monthly" else "assumed_next_year_june_18"
            ),
            "confidence": item.get("confidence", ""),
            "source_url": item.get("source_url", ""),
            "date_evidence": item.get("date_evidence", ""),
            "candidate_release_date_not_used": item.get("candidate_release_date", ""),
            "input_vintage_verified": "no",
            "notes": item.get("notes", ""),
            "selected_on_days": 0, "first_selected_date": "",
        })
    schedule = sorted(records, key=lambda row: (row["available_date"], row["source_period"]))
    daily, availability = [], []
    cursor, current = 0, None
    for label, timestamp in zip(labels, dates):
        while cursor < len(schedule) and parse_date(schedule[cursor]["available_date"]) <= timestamp:
            incoming = schedule[cursor]
            # Late publication of an older period must not overwrite a newer one.
            if current is None or incoming["source_period"] >= current["source_period"]:
                current = incoming
            cursor += 1
        row = {"date": label, factor: current["value"] if current else ""}
        if "period_classification" in input_columns:
            row["period_classification"] = current["period_classification"] if current else ""
        daily.append(row)
        if current:
            current["selected_on_days"] += 1
            if not current["first_selected_date"]:
                current["first_selected_date"] = label
        availability.append({
            "date": label, "factor": factor,
            "source_period": current["source_period"] if current else "",
            "release_date": current["release_date"] if current else "",
            "available_date": current["available_date"] if current else "",
            "date_basis": current["date_basis"] if current else "",
            "days_since_available": (timestamp - parse_date(current["available_date"])).days if current else "",
            "days_since_period_end": (timestamp - period_end(current["source_period"])).days if current else "",
            "is_projection": str("projection" in current["period_classification"].lower()).lower() if current else "",
        })
    output_name = factor.removesuffix("_monthly") + "_daily.csv"
    summary = {
        "file": output_name, "rows": len(daily), "source_periods": len(records),
        "official_release_dates": sum(row["date_basis"].startswith("official_") for row in records),
        "assumed_release_dates": sum(row["date_basis"].startswith("assumed_") for row in records),
        "unavailable_within_calendar": sum(not row["first_eligible_date"] for row in records),
        "source_periods_not_selected": [row["source_period"] for row in records if not row["selected_on_days"]],
        "first_nonmissing_date": next((row["date"] for row in daily if row[factor]), ""),
        "latest_source_period_used": availability[-1]["source_period"],
        "last_value": daily[-1][factor],
    }
    return output_name, input_columns, daily, records, availability, summary


def prepare_events(labels, dates):
    columns, monthly = read_csv(SOURCE / f"{EVENT_STEM}_monthly.csv")
    _, evidence = read_csv(META / "events_date_evidence.csv")
    by_column = {row["event_column"]: row for row in evidence}
    if len(by_column) != len(evidence) or set(by_column) != set(columns[1:]):
        raise ValueError("Event evidence must contain exactly the six source event columns")
    daily = [{column: label if column == "date" else "0" for column in columns} for label in labels]
    for column in columns[1:]:
        active = [row for row in monthly if Decimal(row[column]) != 0]
        if len(active) != 1 or Decimal(active[0][column]) != 1:
            raise ValueError(f"Expected a single monthly event pulse: {column}")
        event_date = parse_date(by_column[column]["event_date"])
        if parse_date(active[0]["date"]).strftime("%Y-%m") != event_date.strftime("%Y-%m"):
            raise ValueError(f"Event date conflicts with source event month: {column}")
        position = bisect.bisect_left(dates, event_date)
        if position < len(dates):
            daily[position][column] = "1"
    return columns, daily


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify outputs without writing")
    args = parser.parse_args()
    _, fx_rows = read_csv(REFERENCE)
    labels = [row["date"] for row in fx_rows]
    dates = [parse_date(value) for value in labels]
    if not dates or dates != sorted(set(dates)):
        raise ValueError("Reference FX dates must be unique and increasing")
    inputs = [REFERENCE, *sorted(SOURCE.glob("*.csv")),
              *sorted(META.glob("*_evidence.csv"))]
    before = {str(path.relative_to(ROOT)): digest(path) for path in inputs}
    outputs, publication_rows, availability_rows, summaries = {}, [], [], []
    for factor, (frequency, evidence_file) in FACTORS.items():
        name, columns, daily, records, available, summary = prepare_factor(
            factor, frequency, evidence_file, labels, dates
        )
        outputs[OUTPUT / name] = csv_text(columns, daily)
        publication_rows.extend(records)
        availability_rows.extend(available)
        summaries.append(summary)
    event_columns, event_rows = prepare_events(labels, dates)
    outputs[OUTPUT / f"{EVENT_STEM}_daily.csv"] = csv_text(event_columns, event_rows)
    outputs[META / "publication_calendar.csv"] = csv_text(list(publication_rows[0]), publication_rows)
    outputs[META / "daily_factor_availability.csv"] = csv_text(list(availability_rows[0]), availability_rows)
    manifest = {
        "reference_file": str(REFERENCE.relative_to(ROOT)),
        "calendar_rows": len(dates), "start": labels[0], "end": labels[-1],
        "alignment": "first reference date on or after availability; latest released statistical period carried forward",
        "intraday_convention": "date-level/end-of-day; no release-hour or FX-session adjustment",
        "fallback_monthly": "15th of next calendar month",
        "fallback_annual": "June 18 of next calendar year",
        "vintage_limitation": "Supplied values preserved; historical first-release vintages not reconstructed.",
        "factors": summaries,
        "event_pulses": {column: sum(row[column] == "1" for row in event_rows) for column in event_columns[1:]},
        "input_sha256": before,
    }
    outputs[META / "alignment_summary.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes() != content.encode("utf-8"):
                raise ValueError(f"Output differs from reproducible alignment: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
    after = {str(path.relative_to(ROOT)): digest(path) for path in inputs}
    if before != after:
        raise ValueError("An input file changed during preparation")
    print(json.dumps({"mode": "check" if args.check else "write", "rows": len(dates),
                      "outputs": len(outputs), "factors": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
