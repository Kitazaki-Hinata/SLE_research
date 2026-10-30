"""Build mutually exclusive actual/IMF daily factors under a simulated calendar.

Run this after prepare_pos_daily_factors.py. --check verifies without writing.
Annual source rows, including historical/initial estimates, are simulation inputs;
their dates are assigned by target year, not historical IMF publication vintages.
"""

import argparse
import csv
import hashlib
import io
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/IMF_predict_data"
OUTPUT = ROOT / "data/3_POS_prediction_daily"
META = OUTPUT / "metadata"
REFERENCE = OUTPUT / "USDSLE_daily.csv"
CALENDAR = META / "publication_calendar.csv"
FACTORS = (
    {
        "factor": "headline_cpi_log_change_monthly",
        "source": "01_CPI_IMF_WEO_Oct2026.csv",
        "column": "cpi_annual_average_index_dec2021_100",
        "prediction_column": "PREDICT_IMF_headline_cpi_log_change_annual",
        "method": "log", "month": 10, "day": 13, "frequency": "monthly",
    },
    {
        "factor": "gdp_annual_pct_change_monthly",
        "source": "02_GDP_Growth_IMF_WEO_Oct2026.csv",
        "column": "real_gdp_growth_pct",
        "prediction_column": "PREDICT_IMF_gdp_annual_pct_change",
        "method": "percent_abs_base", "month": 10, "day": 13, "frequency": "annual",
    },
    {
        "factor": "general_government_gross_debt_annual_change_pp_monthly",
        "source": "03_Government_Debt_GDP_IMF_WEO_Oct2026.csv",
        "column": "general_government_gross_debt_pct_gdp",
        "prediction_column": "PREDICT_IMF_general_government_gross_debt_annual_change_pp",
        "method": "difference", "month": 10, "day": 13, "frequency": "annual",
    },
    {
        "factor": "trade_balance_annual_pct_change_monthly",
        "source": "04_Trade_Balance_IMF_CR_26_168.csv",
        "column": "goods_trade_balance_usd_million",
        "prediction_column": "PREDICT_IMF_trade_balance_annual_pct_change",
        "method": "percent_abs_base", "month": 7, "day": 7, "frequency": "annual",
    },
    {
        "factor": "fx_reserves_log_change_monthly",
        "source": "05_FX_Reserves_IMF_CR_26_168.csv",
        "column": "gross_reserves_excl_swaps_with_rsf_usd_million",
        "prediction_column": "PREDICT_IMF_fx_reserves_log_change_annual",
        "method": "log", "month": 5, "day": 29, "frequency": "monthly",
    },
)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def parse_date(value):
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid date: {value!r}")


def csv_text(columns, rows):
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value):
    if value is None or not value.strip():
        return None
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric input: {value!r}") from exc
    return result if result.is_finite() else None


def difference(current, previous, method):
    """Return a decimal string and missing reason; zero is a valid result."""
    current, previous = number(current), number(previous)
    if current is None:
        return "", "missing_current_value"
    if previous is None:
        return "", "missing_previous_value"
    with localcontext() as context:
        context.prec = 40
        if method == "log":
            if current <= 0 or previous <= 0:
                return "", "nonpositive_log_input"
            value = Decimal(100) * (current.ln() - previous.ln())
        elif method == "percent_abs_base":
            if previous == 0:
                return "", "zero_denominator"
            value = Decimal(100) * (current - previous) / abs(previous)
        elif method == "difference":
            value = current - previous
        else:
            raise ValueError(f"Unknown method: {method}")
        # Fixed precision makes the generated CSV reproducible across runs.
        result = format(value, ".12f").rstrip("0").rstrip(".")
    return ("0" if result in ("", "-0") else result), ""


def forecast_records(config, first_year, last_year):
    _, rows = read_csv(SOURCE / config["source"])
    by_year = {}
    for row in rows:
        year = int(row["year"])
        if year in by_year:
            raise ValueError(f"Duplicate year in {config['source']}: {year}")
        by_year[year] = row
    if not by_year:
        raise ValueError(f"Empty IMF input: {config['source']}")
    records = []
    for year in range(min(first_year, min(by_year)), max(last_year, max(by_year)) + 1):
        current, previous = by_year.get(year), by_year.get(year - 1)
        if current is None:
            value, reason = "", "missing_target_year"
        elif previous is None:
            value, reason = "", "missing_previous_year"
        else:
            value, reason = difference(current.get(config["column"]),
                                       previous.get(config["column"]), config["method"])
        records.append({
            "factor": config["factor"], "target_year": str(year),
            "simulated_update_date": date(year, config["month"], config["day"]).isoformat(),
            "value": value, "missing_reason": reason,
            "method": config["method"], "economic_frequency": "annual",
            "source_file": config["source"], "source_column": config["column"],
            "source_value": current.get(config["column"], "") if current else "",
            "previous_year_value": previous.get(config["column"], "") if previous else "",
            "source_classification": current.get("period_classification", "") if current else "",
            "source_vintage": current.get("forecast_vintage", "") if current else "",
            "source_publication_date": current.get("publication_date", "") if current else "",
            "source_staff_report_date": current.get("staff_report_date", "") if current else "",
            "date_basis": "user_assigned_annual_simulation",
            "historical_forecast_vintage_verified": "no",
        })
    return records


def actual_records(config, calendar_rows):
    records, excluded, seen = [], [], set()
    for row in calendar_rows:
        if row["factor"] != config["factor"]:
            continue
        if "projection" in row["period_classification"].lower():
            excluded.append(row)
            continue
        if number(row["value"]) is None:
            continue
        key = (row["source_period"], row["available_date"])
        if key in seen:
            raise ValueError(f"Duplicate actual release: {config['factor']}, {key}")
        seen.add(key)
        if row["source_frequency"] != config["frequency"]:
            raise ValueError(f"Unexpected actual frequency: {row}")
        parse_date(row["available_date"])
        records.append(row)
    return records, excluded


def align_pair(config, labels, dates, forecasts, actuals, monthly_switch):
    """Apply forecast/actual events once, with actual releases winning ties."""
    events = [(parse_date(row["simulated_update_date"]), 0, row["target_year"], row)
              for row in forecasts]
    events += [(parse_date(row["available_date"]), 1, row["source_period"], row)
               for row in actuals]
    events.sort(key=lambda item: item[:3])
    latest_actual = None
    active_forecast = None
    side = "unavailable"
    cursor = 0
    actual_daily, prediction_daily, audit = [], [], []
    for label, today in zip(labels, dates):
        while cursor < len(events) and events[cursor][0] <= today:
            event_date, kind, _, row = events[cursor]
            cursor += 1
            if kind == 0:
                target_year = int(row["target_year"])
                actual_year = int(latest_actual["source_period"][:4]) if latest_actual else -1
                # A known annual actual (or an actual from a newer year) wins.
                if actual_year > target_year or (
                    actual_year == target_year and config["frequency"] == "annual"
                ):
                    continue
                # No new forecast exists to replace a known actual. However,
                # an active old forecast expires when the next year's is missing.
                if not row["value"] and side != "prediction":
                    continue
                active_forecast, side = row, "prediction"
            else:
                if latest_actual and row["source_period"] < latest_actual["source_period"]:
                    continue
                latest_actual = row
                if side != "prediction":
                    side = "actual"
                    continue
                actual_year = int(row["source_period"][:4])
                target_year = int(active_forecast["target_year"])
                completes_target = (
                    config["frequency"] == "annual"
                    or monthly_switch == "next_release"
                    or row["source_period"].endswith("-12")
                )
                if actual_year > target_year or (actual_year == target_year and completes_target):
                    side = "actual"
        actual_value = latest_actual["value"] if side == "actual" else ""
        forecast_value = active_forecast["value"] if side == "prediction" else ""
        if actual_value and forecast_value:
            raise AssertionError("Actual and prediction overlap")
        actual_daily.append({"date": label, config["factor"]: actual_value})
        prediction_daily.append({"date": label, config["prediction_column"]: forecast_value})
        audit.append({
            "date": label, "factor": config["factor"],
            "active_side": "prediction_missing" if side == "prediction" and not forecast_value else side,
            "active_target_year": (active_forecast["target_year"] if side == "prediction" else
                                   latest_actual["source_period"][:4] if side == "actual" else ""),
            "actual_source_period": latest_actual["source_period"] if latest_actual else "",
            "actual_available_date": latest_actual["available_date"] if latest_actual else "",
            "actual_classification": latest_actual["period_classification"] if latest_actual else "",
            "prediction_target_year": active_forecast["target_year"] if active_forecast else "",
            "prediction_update_date": active_forecast["simulated_update_date"] if active_forecast else "",
            "prediction_missing_reason": active_forecast["missing_reason"] if side == "prediction" else "",
            "actual_value": actual_value, "prediction_value": forecast_value,
        })
    return actual_daily, prediction_daily, audit


def build_outputs(monthly_switch="next_release", reserves_scenario="with_rsf"):
    _, reference = read_csv(REFERENCE)
    labels = [row["date"] for row in reference]
    dates = [parse_date(label) for label in labels]
    if not dates or dates != sorted(set(dates)):
        raise ValueError("FX calendar must be nonempty, unique and increasing")
    _, calendar_rows = read_csv(CALENDAR)
    input_paths = [REFERENCE, CALENDAR, *(SOURCE / config["source"] for config in FACTORS)]
    hashes = {str(path.relative_to(ROOT)): digest(path) for path in input_paths}
    outputs, all_forecasts, all_audit, summaries, excluded_rows = {}, [], [], [], []
    for specification in FACTORS:
        config = dict(specification)
        if config["factor"] == "fx_reserves_log_change_monthly":
            config["column"] = f"gross_reserves_excl_swaps_{reserves_scenario}_usd_million"
        forecasts = forecast_records(config, dates[0].year, dates[-1].year)
        actuals, excluded = actual_records(config, calendar_rows)
        actual, prediction, audit = align_pair(config, labels, dates, forecasts, actuals, monthly_switch)
        filename = config["factor"].removesuffix("_monthly") + "_daily.csv"
        outputs[OUTPUT / filename] = csv_text(["date", config["factor"]], actual)
        outputs[OUTPUT / ("PREDICT_IMF_" + filename)] = csv_text(["date", config["prediction_column"]], prediction)
        all_forecasts.extend(forecasts)
        all_audit.extend(audit)
        excluded_rows.extend(excluded)
        summaries.append({
            "factor": config["factor"], "actual_file": filename,
            "prediction_file": "PREDICT_IMF_" + filename,
            "source_column": config["column"], "difference_method": config["method"],
            "annual_update_month_day": f"{config['month']:02}-{config['day']:02}",
            "actual_nonmissing_days": sum(bool(row[config["factor"]]) for row in actual),
            "prediction_nonmissing_days": sum(bool(row[config["prediction_column"]]) for row in prediction),
            "both_missing_days": sum(not row["actual_value"] and not row["prediction_value"] for row in audit),
            "overlap_days": sum(bool(row["actual_value"] and row["prediction_value"]) for row in audit),
            "missing_prediction_years": {row["target_year"]: row["missing_reason"] for row in forecasts if row["missing_reason"]},
        })
    outputs[META / "imf_prediction_calendar.csv"] = csv_text(list(all_forecasts[0]), all_forecasts)
    outputs[META / "imf_prediction_daily_availability.csv"] = csv_text(list(all_audit[0]), all_audit)
    summary = {
        "mode": "synthetic_annual_release_calendar_not_real_time_forecast_vintages",
        "calendar_rows": len(dates), "start": labels[0], "end": labels[-1],
        "monthly_actual_switch": monthly_switch, "reserves_scenario": reserves_scenario,
        "forecast_scope": "All supplied annual rows, including actual/preliminary rows, are simulated forecast inputs.",
        "missing_policy": "No interpolation or fallback across missing years. A missing new prediction does not mask an active actual; if the previous forecast is still active, it expires and stays blank until an eligible actual or a new forecast arrives.",
        "intraday_convention": "Date-level: a release takes effect on that calendar day; eligible actual wins same-day ties.",
        "frequency_note": "CPI and reserves forecast differences are annual; existing actual differences remain monthly.",
        "vintage_note": "User-assigned dates can precede real source publications. These outputs are not leakage-free historical forecasts.",
        "actual_calendar": str(CALENDAR.relative_to(ROOT)),
        "excluded_actual_projections": [{key: row[key] for key in (
            "factor", "source_period", "value", "available_date", "period_classification"
        )} for row in excluded_rows],
        "factors": summaries, "input_sha256": hashes,
    }
    outputs[META / "imf_prediction_summary.json"] = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if hashes != {str(path.relative_to(ROOT)): digest(path) for path in input_paths}:
        raise ValueError("An input changed while building the outputs")
    return outputs, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify generated files without writing")
    parser.add_argument("--monthly-switch", choices=("next_release", "december_release"), default="next_release")
    parser.add_argument("--reserves-scenario", choices=("with_rsf", "without_rsf"), default="with_rsf")
    args = parser.parse_args()
    outputs, summary = build_outputs(args.monthly_switch, args.reserves_scenario)
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_bytes() != content.encode("utf-8"):
                raise ValueError(f"Output differs from reproducible preparation: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="")
    print(json.dumps({"mode": "check" if args.check else "write", "outputs": len(outputs),
                      "rows_per_file": summary["calendar_rows"], "factors": summary["factors"]},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
