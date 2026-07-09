#!/usr/bin/env python3
"""
Weekly data refresh for Housing Market Explorer.

Hybrid approach:
- Loads existing data.json as baseline (preserves static fields like FEMA, Census, AQI, etc.)
- Updates DYNAMIC fields: Zillow home prices/rents, FRED mortgage rates
- Recalculates derived metrics (price-to-income, monthly payment, etc.)
- Saves updated data.json + historical snapshot

API keys via env vars: FRED_API_KEY, CENSUS_API_KEY, BEA_API_KEY
"""

import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "data.json"
RAW = ROOT / "raw_data"
RAW.mkdir(exist_ok=True)

FRED_KEY = os.environ.get("FRED_API_KEY", "")
CENSUS_KEY = os.environ.get("CENSUS_API_KEY", "")
BEA_KEY = os.environ.get("BEA_API_KEY", "")

def log(status, msg):
    icon = {"OK": "✓", "FAIL": "✗", "INFO": "⚠"}[status]
    print(f"  {icon} {msg}")


def load_baseline():
    """Load existing data.json as the baseline."""
    if OUT.exists():
        with open(OUT) as f:
            records = json.load(f)
        log("OK", f"Loaded baseline: {len(records)} metros")
        return {r["RegionName"]: r for r in records}
    log("FAIL", "No baseline data.json found")
    return {}


def pull_zillow_prices():
    """Pull latest Zillow home prices and rents."""
    print("\n=== Zillow ===")
    base = "https://files.zillowstatic.com/research/public_csvs"
    result = {}

    # ZHVI (home values)
    try:
        df = pd.read_csv(f"{base}/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv")
        date_cols = [c for c in df.columns if c[:4].isdigit()]
        latest = date_cols[-1] if date_cols else None
        yr_ago = None
        if latest:
            yr = int(latest[:4])
            mo = latest[5:7]
            cand = f"{yr-1}-{mo}-01"
            if cand in date_cols:
                yr_ago = cand

        for _, row in df.iterrows():
            name = str(row.get("RegionName", ""))
            if not name or name == "United States":
                continue
            entry = {"zhvi_current": row[latest] if latest else None}
            if yr_ago:
                try:
                    entry["price_chg_1yr_pct"] = round((row[latest] / row[yr_ago] - 1) * 100, 2)
                except (TypeError, ZeroDivisionError):
                    pass
            result[name] = entry

        log("OK", f"Home prices: {len(result)} metros, latest={latest}")
    except Exception as e:
        log("FAIL", f"ZHVI: {e}")

    # ZORI (rents)
    try:
        df = pd.read_csv(f"{base}/zori/Metro_zori_uc_sfrcondomfr_sm_sa_month.csv")
        date_cols = [c for c in df.columns if c[:4].isdigit()]
        latest = date_cols[-1] if date_cols else None
        matched = 0
        for _, row in df.iterrows():
            name = str(row.get("RegionName", ""))
            if name in result and latest:
                result[name]["zori_rent"] = row[latest]
                matched += 1
        log("OK", f"Rents: {matched} metros updated")
    except Exception as e:
        log("FAIL", f"ZORI: {e}")

    return result


def pull_mortgage_rate():
    """Get current 30-year mortgage rate from FRED."""
    print("\n=== FRED ===")
    if not FRED_KEY:
        log("FAIL", "No FRED API key")
        return 6.5
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit=1"
        resp = requests.get(url, timeout=15).json()
        rate = float(resp["observations"][0]["value"])
        log("OK", f"30Y mortgage rate: {rate}%")
        return rate
    except Exception as e:
        log("FAIL", f"FRED: {e}")
        return 6.5


def update_derived(record, mortgage_rate):
    """Recalculate derived metrics based on updated prices."""
    zhvi = record.get("zhvi_current")
    income = record.get("median_hh_income")
    rent = record.get("zori_rent")

    if zhvi and income:
        record["price_to_income"] = round(zhvi / income, 2)
        monthly_rate = (mortgage_rate / 100) / 12
        loan = zhvi * 0.8
        if monthly_rate > 0:
            payment = loan * monthly_rate * (1 + monthly_rate)**360 / ((1 + monthly_rate)**360 - 1)
            record["monthly_payment"] = round(payment, 0)
            record["payment_pct_income"] = round(payment / (income / 12) * 100, 1)

    if zhvi and rent and rent > 0:
        record["price_to_rent"] = round(zhvi / (rent * 12), 2)
        record["gross_rental_yield"] = round(rent * 12 / zhvi * 100, 2)
        if record.get("monthly_payment"):
            record["payment_vs_rent"] = round(record["monthly_payment"] - rent, 0)


def main():
    print("=" * 60)
    print("HOUSING MARKET DATA REFRESH (Hybrid)")
    print("=" * 60)
    print(f"Date: {date.today()}")
    print(f"FRED key: {'set' if FRED_KEY else 'MISSING'}")

    # 1. Load baseline
    baseline = load_baseline()
    if not baseline:
        print("ERROR: No baseline data. Run the initial data build first.")
        sys.exit(1)

    # 2. Pull fresh Zillow data
    zillow = pull_zillow_prices()

    # 3. Pull mortgage rate
    mortgage_rate = pull_mortgage_rate()

    # 4. Merge updates into baseline
    print("\n=== Merging ===")
    updated = 0
    for name, record in baseline.items():
        if name in zillow:
            z = zillow[name]
            # Update dynamic fields
            if z.get("zhvi_current") is not None:
                record["zhvi_current"] = round(z["zhvi_current"], 2)
            if z.get("zori_rent") is not None:
                record["zori_rent"] = round(z["zori_rent"], 2)
            if z.get("price_chg_1yr_pct") is not None:
                record["price_chg_1yr_pct"] = z["price_chg_1yr_pct"]
            # Recalculate derived
            update_derived(record, mortgage_rate)
            updated += 1

        # Stamp the date
        record["_data_date"] = date.today().isoformat()

    log("OK", f"Updated {updated}/{len(baseline)} metros with fresh prices")

    # 5. Export
    print("\n=== Export ===")
    records = list(baseline.values())
    with open(OUT, "w") as f:
        json.dump(records, f, separators=(",", ":"))
    log("OK", f"{len(records)} metros → {OUT.name} ({OUT.stat().st_size/1024:.0f} KB)")

    # 6. Historical snapshot
    history_dir = ROOT / "history"
    history_dir.mkdir(exist_ok=True)
    snapshot = history_dir / f"{date.today().isoformat()}.json"
    with open(snapshot, "w") as f:
        json.dump(records, f, separators=(",", ":"))
    log("OK", f"Snapshot: {snapshot.name}")

    print(f"\n{'='*60}")
    print("DONE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

