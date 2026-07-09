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


def pull_census_acs5():
    """Pull Census ACS 5-year for all metros (covers small metros that ACS 1-year misses)."""
    print("\n=== Census ACS 5-year ===")
    if not CENSUS_KEY:
        log("FAIL", "No Census API key")
        return None
    try:
        variables = "NAME,B19013_001E,B01003_001E,B25064_001E,B01002_001E,B17001_002E,B15003_022E,B25003_002E,B08006_001E,B08006_017E"
        url = f"https://api.census.gov/data/2023/acs/acs5?get={variables}&for=metropolitan%20statistical%20area/micropolitan%20statistical%20area:*&key={CENSUS_KEY}"
        resp = requests.get(url, timeout=60)
        rows = resp.json()

        lookup = {}
        for row in rows[1:]:
            name = row[0]
            city = name.split(",")[0].split("-")[0].strip().lower()
            state_match = re.search(r",\s*([A-Z]{2})", name)
            state = state_match.group(1) if state_match else ""

            def safe_int(v):
                try: return int(v) if v and v != "null" else None
                except: return None
            def safe_float(v):
                try: return float(v) if v and v != "null" else None
                except: return None

            pop = safe_int(row[2])
            income = safe_int(row[1])
            rent = safe_int(row[3])
            age = safe_float(row[4])
            poverty_ct = safe_int(row[5])
            bach_ct = safe_int(row[6])
            owner_occ = safe_int(row[7])
            commuters = safe_int(row[8])
            wfh = safe_int(row[9])

            entry = {"population": pop, "median_hh_income": income, "median_rent_census": rent, "median_age": age}
            if pop and poverty_ct:
                entry["poverty_rate"] = round(poverty_ct / pop * 100, 1)
            if pop and bach_ct:
                entry["bachelors_pct"] = round(bach_ct / pop * 100, 1)
            if pop and owner_occ:
                entry["homeownership_rate"] = min(round(owner_occ / (pop * 0.38) * 100, 1), 95)
            if commuters and wfh:
                entry["pct_wfh"] = round(wfh / commuters * 100, 1)

            lookup[(city, state)] = entry

        log("OK", f"{len(lookup)} metros from ACS 5-year")
        return lookup
    except Exception as e:
        log("FAIL", f"Census ACS 5-year: {e}")
        return None


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

    # 4. Check for new Zillow metros not in our baseline
    print("\n=== New Metros ===")
    new_metros = 0
    for name, z in zillow.items():
        if name not in baseline and name != "United States":
            # Parse state from "City, ST"
            state = ""
            if ", " in name:
                state = name.split(", ")[-1].strip()
            baseline[name] = {
                "RegionName": name,
                "StateName": state,
                "state_abbr": state,
                "zhvi_current": round(z["zhvi_current"], 2) if z.get("zhvi_current") else None,
                "zori_rent": round(z["zori_rent"], 2) if z.get("zori_rent") else None,
                "_source_dates": {"zillow": date.today().strftime("%Y-%m")},
            }
            new_metros += 1
    if new_metros:
        log("OK", f"Added {new_metros} new metros from Zillow")
    else:
        log("OK", "No new metros")

    # 5. Check which metros need Census data, pull if needed
    missing_census = [n for n, r in baseline.items() if r.get("population") is None]
    census = None
    if missing_census:
        log("INFO", f"{len(missing_census)} metros missing Census data — pulling ACS 5-year")
        census = pull_census_acs5()

    # 6. Merge updates into baseline
    print("\n=== Merging ===")
    updated = 0
    census_filled = 0
    for name, record in baseline.items():
        # Update Zillow prices
        if name in zillow:
            z = zillow[name]
            if z.get("zhvi_current") is not None:
                record["zhvi_current"] = round(z["zhvi_current"], 2)
            if z.get("zori_rent") is not None:
                record["zori_rent"] = round(z["zori_rent"], 2)
            if z.get("price_chg_1yr_pct") is not None:
                record["price_chg_1yr_pct"] = z["price_chg_1yr_pct"]
            updated += 1

        # Backfill Census data for metros that don't have it
        if record.get("population") is None and census:
            city = name.split(",")[0].split("-")[0].strip().lower()
            state = record.get("state_abbr", "")
            key = (city, state)
            if key in census:
                for k, v in census[key].items():
                    if v is not None:
                        record[k] = v
                if not record.get("_source_dates"):
                    record["_source_dates"] = {}
                if isinstance(record["_source_dates"], dict):
                    record["_source_dates"]["census"] = "2023 (5yr)"
                census_filled += 1

        # Recalculate derived metrics with latest prices + income
        update_derived(record, mortgage_rate)

        # Stamp the date
        record["_data_date"] = date.today().isoformat()

    log("OK", f"Updated {updated}/{len(baseline)} metros with fresh prices")
    if census_filled:
        log("OK", f"Backfilled Census data for {census_filled} metros")
    log("OK", f"Total metros: {len(baseline)}")

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

