"""Boundary checks for simulated IMF release dates and mutually exclusive factors."""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_imf_prediction_daily as subject


def configuration(frequency="annual"):
    return {
        "factor": "actual_factor",
        "prediction_column": "prediction_factor",
        "frequency": frequency,
        "source": "fixture.csv",
        "column": "value",
        "method": "percent_abs_base",
        "month": 10,
        "day": 13,
    }


def prediction(year, value="10", missing_reason="", release=None):
    return {
        "target_year": str(year),
        "simulated_update_date": release or f"{year}-10-13",
        "value": value,
        "missing_reason": missing_reason,
    }


def actual(period, released, value="2", classification="", frequency="annual"):
    return {
        "factor": "actual_factor",
        "source_frequency": frequency,
        "source_period": period,
        "available_date": released,
        "value": value,
        "period_classification": classification,
    }


def align(labels, predictions, actuals, frequency="annual", monthly_switch="next_release"):
    dates = [date.fromisoformat(label) for label in labels]
    actual_rows, predicted_rows, audit = subject.align_pair(
        configuration(frequency), labels, dates, predictions, actuals, monthly_switch
    )
    pairs = [(a["actual_factor"], p["prediction_factor"])
             for a, p in zip(actual_rows, predicted_rows)]
    return pairs, audit


class DifferenceTests(unittest.TestCase):
    def test_negative_base_preserves_improvement_sign(self):
        self.assertEqual(subject.difference("-80", "-100", "percent_abs_base"), ("20", ""))
        self.assertEqual(subject.difference("-120", "-100", "percent_abs_base"), ("-20", ""))

    def test_ordinary_difference_keeps_sign(self):
        self.assertEqual(subject.difference("45.419", "50.139", "difference"), ("-4.72", ""))

    def test_log_difference_uses_levels_and_percent_scale(self):
        value, reason = subject.difference("392", "410", "log")
        self.assertEqual(reason, "")
        self.assertAlmostEqual(float(value), -4.489531990789099, places=10)

    def test_zero_is_not_missing(self):
        for method in ("log", "percent_abs_base", "difference"):
            with self.subTest(method=method):
                self.assertEqual(subject.difference("12", "12", method), ("0", ""))
        self.assertEqual(subject.difference("0", "20", "percent_abs_base"), ("-100", ""))
        self.assertEqual(subject.difference("0", "0", "difference"), ("0", ""))

    def test_invalid_difference_inputs_are_missing(self):
        cases = [
            (None, "5", "difference", "missing_current_value"),
            ("5", "", "difference", "missing_previous_value"),
            ("NaN", "5", "difference", "missing_current_value"),
            ("5", "Infinity", "difference", "missing_previous_value"),
            ("5", "0", "percent_abs_base", "zero_denominator"),
            ("0", "5", "log", "nonpositive_log_input"),
            ("5", "0", "log", "nonpositive_log_input"),
            ("-5", "-4", "log", "nonpositive_log_input"),
        ]
        for current, previous, method, expected in cases:
            with self.subTest(current=current, previous=previous, method=method):
                self.assertEqual(subject.difference(current, previous, method), ("", expected))

    def test_forecasts_never_difference_across_missing_year(self):
        rows = [{"year": "2023", "value": "10"},
                {"year": "2025", "value": "20"},
                {"year": "2026", "value": "30"}]
        with patch.object(subject, "read_csv", return_value=(["year", "value"], rows)):
            records = subject.forecast_records(configuration(), 2023, 2026)
        by_year = {row["target_year"]: row for row in records}
        self.assertEqual(by_year["2023"]["missing_reason"], "missing_previous_year")
        self.assertEqual(by_year["2024"]["missing_reason"], "missing_target_year")
        self.assertEqual(by_year["2025"]["value"], "")
        self.assertEqual(by_year["2025"]["missing_reason"], "missing_previous_year")
        self.assertEqual(by_year["2026"]["value"], "50")


class ReleaseSwitchTests(unittest.TestCase):
    def test_gdp_switches_exactly_on_release_days(self):
        pairs, audit = align(
            ["2025-10-12", "2025-10-13", "2026-06-17", "2026-06-18"],
            [prediction(2025, "10")],
            [actual("2024", "2025-06-18", "-20"),
             actual("2025", "2026-06-18", "7")],
        )
        self.assertEqual(pairs, [("-20", ""), ("", "10"), ("", "10"), ("7", "")])
        self.assertEqual(audit[-1]["active_target_year"], "2025")

    def test_same_day_actual_wins_and_zero_remains_active(self):
        pairs, audit = align(
            ["2025-10-13"], [prediction(2025)],
            [actual("2025", "2025-10-13", "0")],
        )
        self.assertEqual(pairs, [("0", "")])
        self.assertEqual(audit[0]["active_side"], "actual")

    def test_known_annual_actual_is_not_replaced_by_prediction(self):
        pairs, _ = align(
            ["2025-10-13"], [prediction(2025)],
            [actual("2025", "2025-10-01", "2")],
        )
        self.assertEqual(pairs, [("2", "")])

    def test_late_old_year_does_not_end_new_year_forecast(self):
        pairs, audit = align(
            ["2026-10-13", "2026-10-20"], [prediction(2026, "30")],
            [actual("2024", "2025-06-18", "1"),
             actual("2025", "2026-10-20", "2")],
        )
        self.assertEqual(pairs, [("", "30"), ("", "30")])
        self.assertEqual(audit[-1]["active_target_year"], "2026")

    def test_existing_same_year_monthly_actual_does_not_cancel_new_forecast(self):
        pairs, _ = align(
            ["2025-10-12", "2025-10-13", "2025-10-14"], [prediction(2025)],
            [actual("2025-08", "2025-09-15", "1", frequency="monthly")],
            frequency="monthly",
        )
        self.assertEqual(pairs, [("1", ""), ("", "10"), ("", "10")])

    def test_monthly_switch_modes_use_distinct_release_events(self):
        labels = ["2024-10-13", "2024-10-15", "2025-01-15"]
        actuals = [actual("2024-09", "2024-10-15", "3", frequency="monthly"),
                   actual("2024-12", "2025-01-15", "4", frequency="monthly")]
        next_pairs, _ = align(labels, [prediction(2024)], actuals, frequency="monthly")
        december_pairs, _ = align(
            labels, [prediction(2024)], actuals, frequency="monthly", monthly_switch="december_release"
        )
        self.assertEqual(next_pairs, [("", "10"), ("3", ""), ("4", "")])
        self.assertEqual(december_pairs, [("", "10"), ("", "10"), ("4", "")])

    def test_monthly_actual_from_later_year_ends_forecast_in_both_modes(self):
        for mode in ("next_release", "december_release"):
            with self.subTest(mode=mode):
                pairs, _ = align(
                    ["2026-02-15"], [prediction(2025)],
                    [actual("2026-01", "2026-02-15", "5", frequency="monthly")],
                    frequency="monthly", monthly_switch=mode,
                )
                self.assertEqual(pairs, [("5", "")])

    def test_missing_new_year_prediction_does_not_carry_previous_forecast(self):
        pairs, audit = align(
            ["2025-10-13", "2026-10-13", "2026-10-20", "2027-06-18"],
            [prediction(2025, "10"), prediction(2026, "", "missing_target_year")],
            [actual("2025", "2026-10-20", "5"), actual("2026", "2027-06-18", "6")],
        )
        self.assertEqual(pairs, [("", "10"), ("", ""), ("", ""), ("6", "")])
        self.assertEqual(audit[1]["active_side"], "prediction_missing")
        self.assertEqual(audit[2]["prediction_missing_reason"], "missing_target_year")

    def test_missing_scheduled_prediction_preserves_existing_actual(self):
        pairs, audit = align(
            ["2025-10-12", "2025-10-13"],
            [prediction(2025, "", "missing_previous_year")],
            [actual("2024", "2025-06-18", "4")],
        )
        self.assertEqual(pairs, [("4", ""), ("4", "")])
        self.assertEqual(audit[-1]["active_side"], "actual")

    def test_zero_prediction_stays_nonmissing(self):
        pairs, audit = align(["2025-10-13"], [prediction(2025, "0")], [])
        self.assertEqual(pairs, [("", "0")])
        self.assertEqual(audit[0]["active_side"], "prediction")

    def test_explicit_debt_projection_is_excluded_before_alignment(self):
        historical = actual("2025", "2026-04-14", "-1.5", "Earlier year")
        projected = actual("2026", "2026-04-14", "-0.9", "Projection (2026+)")
        rows, excluded = subject.actual_records(configuration(), [historical, projected])
        self.assertEqual(rows, [historical])
        self.assertEqual(excluded, [projected])
        pairs, _ = align(["2026-04-14"], [prediction(2025)], rows)
        self.assertEqual(pairs, [("-1.5", "")])


if __name__ == "__main__":
    unittest.main()
