"""Collect official CPI publication dates without changing factor values.

Only the evidence CSV is persistent; PDFs are parsed in memory.
Optional research dependencies: requests, beautifulsoup4, pypdf.
The daily alignment script does not need these dependencies or network access.
"""

import concurrent.futures
import csv
import datetime as dt
import io
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://www.statistics.sl/"
INDEX = urljoin(BASE, "index.php/cpi.html")
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/2_regression_monthly/headline_cpi_log_change_monthly.csv"
OUT = ROOT / "data/3_POS_prediction_daily/metadata/cpi_release_evidence.csv"
MONTHS = {dt.date(2000, m, 1).strftime("%B").lower(): m for m in range(1, 13)}
MONTH_RE = "|".join(MONTHS)
DATE_RE = re.compile(
    rf"(?P<day>\d{{1,2}})\s*(?:st|nd|rd|th)?\s*(?P<month>{MONTH_RE})\s*[,./-]?\s*(?P<year>20\d{{2}})",
    re.I,
)
MONTH_FIRST_RE = re.compile(
    rf"(?P<month>{MONTH_RE})\s*(?P<day>\d{{1,2}})\s*(?:st|nd|rd|th)?\s*[,./-]?\s*(?P<year>20\d{{2}})",
    re.I,
)
FIELDS = ["period", "release_date", "source_url", "date_evidence", "confidence", "notes"]


def get(url):
    for attempt in range(3):
        response = requests.get(url, timeout=(15, 45))
        if response.status_code not in (429, 502, 503, 504) or attempt == 2:
            response.raise_for_status()
            return response
        time.sleep(2 + attempt * 2)


def parse_pdf(period, url, reader):
    row = dict.fromkeys(FIELDS, "")
    row.update(period=period, source_url=url, confidence="missing")
    try:
        content = get(url).content
        if not content.startswith(b"%PDF"):
            raise ValueError("URL did not return a PDF")
        pdf = reader(io.BytesIO(content))
        text = re.sub(r"\s+", " ", pdf.pages[0].extract_text() or "").strip()
        issue_title = re.search(rf"CONSUMER\s+PRICE\s+INDEX.{{0,70}}?\b({MONTH_RE})\s*[,/-]?\s*(20\d{{2}})\b", text, re.I)
        issue_seen = bool(issue_title and f"{issue_title[2]}-{MONTHS[issue_title[1].lower()]:02}" == period)
        released = re.search(r"\bReleased\s*:?\s*(.{0,110})", text, re.I)
        candidate = (DATE_RE.search(released.group(1)) or MONTH_FIRST_RE.search(released.group(1))) if released else None
        if candidate:
            when = dt.date(int(candidate["year"]), MONTHS[candidate["month"].lower()], int(candidate["day"]))
            issue_start = dt.date.fromisoformat(period + "-01")
            issue_end = (issue_start.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
            row["date_evidence"] = "Released " + released.group(1)[:candidate.end()].strip()
            if not issue_seen:
                row["confidence"] = "ambiguous_period"
                row["notes"] = "Requested month/year not confirmed in first-page CPI title; possible archive mislink."
            elif when <= issue_end or (when - issue_end).days > 180:
                row["confidence"] = "ambiguous_date"
                row["notes"] = "Printed release date is not within 1 to 180 days after the statistical month; requires review."
                weekday = re.search(r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", released.group(1), re.I)
                if weekday and weekday.group(1).lower() != when.strftime("%A").lower():
                    row["notes"] += " Printed weekday also disagrees with the calendar. No correction inferred."
            else:
                row["release_date"] = when.isoformat()
                row["confidence"] = "official_explicit_release_date"
                row["notes"] = "Date printed on official CPI release first page; not independently verified as initial upload date. Existing CPI values retain their current vintage."
        else:
            row["notes"] = "No parseable explicit Released date on first page."
        if not row["release_date"]:
            row["_review_text"] = text[:350]
    except Exception as exc:
        row["notes"] = f"Fetch or parse failed: {type(exc).__name__}: {str(exc)[:220]}"
    return row


def main(reader):
    with SOURCE.open(encoding="utf-8-sig", newline="") as file:
        periods = [r["date"][:7] for r in csv.DictReader(file) if r["headline_cpi_log_change_monthly"].strip()]
    soup = BeautifulSoup(get(INDEX).content, "html.parser")
    links = {}
    for anchor in soup.find_all("a", href=True):
        label = anchor.get_text(" ", strip=True)
        matched = re.fullmatch(r"CPI Press Release\s+(\w+)\s+(\d{4})", label, re.I)
        if matched and matched[1].lower() in MONTHS:
            links[f"{matched[2]}-{MONTHS[matched[1].lower()]:02}"] = urljoin(BASE, anchor["href"])
    output = []
    if OUT.exists():
        with OUT.open(encoding="utf-8-sig", newline="") as file:
            output = [r for r in csv.DictReader(file) if r["release_date"] and r["period"] in periods]
    completed = {r["period"] for r in output}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        pending = {pool.submit(parse_pdf, period, links[period], reader): period for period in periods if period in links and period not in completed}
        for future in concurrent.futures.as_completed(pending):
            row = future.result()
            output.append(row)
            if len(output) % 10 == 0:
                print(f"Reviewed {len(output)}/{len(periods)}; confirmed {sum(bool(r['release_date']) for r in output)}", flush=True)
    for period in periods:
        if period not in links and period not in completed:
            row = dict.fromkeys(FIELDS, "")
            row.update(period=period, confidence="missing", notes="No link found on official CPI archive page.", source_url=INDEX)
            output.append(row)
    output.sort(key=lambda r: r["period"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output)
    print(json.dumps({"rows": len(output), "confirmed": sum(bool(r["release_date"]) for r in output), "path": str(OUT)}, ensure_ascii=False), flush=True)
    for row in output:
        if not row["release_date"]:
            print(json.dumps(row, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit("CPI evidence collection requires the optional pypdf package.") from exc
    main(PdfReader)
