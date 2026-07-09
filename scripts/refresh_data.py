#!/usr/bin/env python3
"""
Refresh housing market data from public sources.
Pulls from Zillow, Redfin, Realtor, Census, FRED, BEA, FEMA, EIA.
Outputs assets/data.json for the static site.

API keys via env vars: FRED_API_KEY, CENSUS_API_KEY, BEA_API_KEY
"""

import json
import os
import sys
import time
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

# City coordinates for geocoding
COORDS_URL = "https://raw.githubusercontent.com/kelvins/US-Cities-Database/main/csv/us_cities.csv"

# State abbreviation helpers
STATE_FIPS = {
    "01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE",
    "11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA",
    "20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN",
    "28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM",
    "36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI",
    "45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA",
    "54":"WV","55":"WI","56":"WY",
}


def log(src, status, msg):
    icon = "✓" if status == "OK" else "✗" if status == "FAIL" else "⚠"
    print(f"  {icon} [{src}] {msg}")


# ═══════════════════════════════════════════
# 1. ZILLOW — direct CSV downloads (no key)
# ═══════════════════════════════════════════
def pull_zillow():
    print("\n=== Zillow ===")
    base = "https://files.zillowstatic.com/research/public_csvs"
    files = {
        "zhvi_metro": f"{base}/zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
        "zori_metro": f"{base}/zori/Metro_zori_uc_sfrcondomfr_sm_sa_month.csv",
        "inventory": f"{base}/invt_fs/Metro_invt_fs_uc_sfrcondo_sm_month.csv",
        "price_cuts": f"{base}/perc_listings_price_cut/Metro_perc_listings_price_cut_uc_sfrcondo_sm_month.csv",
        "sale_to_list": f"{base}/mean_sale_to_list/Metro_mean_sale_to_list_uc_sfrcondo_sm_month.csv",
        "new_listings": f"{base}/new_listings/Metro_new_listings_uc_sfrcondo_sm_month.csv",
    }
    results = {}
    for name, url in files.items():
        try:
            df = pd.read_csv(url)
            (RAW / f"zillow_{name}.csv").open("w").write(df.to_csv(index=False))
            results[name] = df
            log("Zillow", "OK", f"{name}: {len(df)} rows")
        except Exception as e:
            log("Zillow", "FAIL", f"{name}: {e}")
    return results


# ═══════════════════════════════════════════
# 2. REDFIN — direct TSV download (no key)
# ═══════════════════════════════════════════
def pull_redfin():
    print("\n=== Redfin ===")
    url = "https://redfin-public-data.s3.us-west-2.amazonaws.com/redfin_market_tracker/redfin_metro_market_tracker.tsv000.gz"
    try:
        df = pd.read_csv(url, sep="\t", compression="gzip")
        # Normalize column names to lowercase
        df.columns = df.columns.str.lower()
        # Keep latest month only
        df["period_end"] = pd.to_datetime(df["period_end"])
        latest = df["period_end"].max()
        df = df[df["period_end"] == latest]
        log("Redfin", "OK", f"{len(df)} metros, period={latest.date()}")
        return df
    except Exception as e:
        log("Redfin", "FAIL", str(e))
        return None


# ═══════════════════════════════════════════
# 3. FRED — mortgage rate for payment calc
# ═══════════════════════════════════════════
def pull_fred():
    print("\n=== FRED ===")
    if not FRED_KEY:
        log("FRED", "FAIL", "No API key")
        return None
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit=1"
        resp = requests.get(url, timeout=15).json()
        rate = float(resp["observations"][0]["value"])
        log("FRED", "OK", f"30Y mortgage rate: {rate}%")
        return rate
    except Exception as e:
        log("FRED", "FAIL", str(e))
        return 6.5  # fallback


# ═══════════════════════════════════════════
# 4. CENSUS ACS — income, demographics
# ═══════════════════════════════════════════
def pull_census():
    print("\n=== Census ACS ===")
    if not CENSUS_KEY:
        log("Census", "FAIL", "No API key")
        return None
    try:
        year = 2023
        variables = "NAME,B19013_001E,B25064_001E,B01003_001E,B25077_001E,B01002_001E,B17001_002E,B15003_022E,B25003_002E,B08006_001E,B08006_003E,B08006_017E"
        url = f"https://api.census.gov/data/{year}/acs/acs1?get={variables}&for=metropolitan%20statistical%20area/micropolitan%20statistical%20area:*&key={CENSUS_KEY}"
        resp = requests.get(url, timeout=30)
        data = resp.json()
        df = pd.DataFrame(data[1:], columns=data[0])
        # Rename columns
        df = df.rename(columns={
            "B19013_001E": "median_hh_income",
            "B25064_001E": "median_rent_census",
            "B01003_001E": "population",
            "B25077_001E": "median_home_value_census",
            "B01002_001E": "median_age",
            "B17001_002E": "poverty_count",
            "B15003_022E": "bachelors_count",
            "B25003_002E": "owner_occupied",
            "B08006_001E": "commuters_total",
            "B08006_003E": "drive_alone",
            "B08006_017E": "wfh",
            "metropolitan statistical area/micropolitan statistical area": "cbsa_code",
        })
        # Convert to numeric
        for c in df.columns:
            if c not in ("NAME", "cbsa_code"):
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["cbsa_code"] = df["cbsa_code"].astype(str)
        log("Census", "OK", f"{len(df)} metros, year={year}")
        return df
    except Exception as e:
        log("Census", "FAIL", str(e))
        return None


# ═══════════════════════════════════════════
# 5. BUILD FINAL DATASET
# ═══════════════════════════════════════════
def build_dataset(zillow, redfin, mortgage_rate, census):
    print("\n=== Building Dataset ===")

    # Start with Zillow ZHVI
    zhvi = zillow.get("zhvi_metro")
    if zhvi is None:
        print("  No Zillow data, cannot continue")
        return None

    # Get latest month columns
    date_cols = [c for c in zhvi.columns if c[:4].isdigit()]
    latest_col = date_cols[-1] if date_cols else None
    yr_ago_col = None
    five_ago_col = None
    if latest_col:
        yr = int(latest_col[:4])
        mo = latest_col[5:7]
        yr_ago_col = f"{yr-1}-{mo}-01" if f"{yr-1}-{mo}-01" in date_cols else None
        five_ago_col = f"{yr-5}-{mo}-01" if f"{yr-5}-{mo}-01" in date_cols else None

    df = pd.DataFrame()
    df["RegionName"] = zhvi["RegionName"]
    df["StateName"] = zhvi["StateName"] if "StateName" in zhvi.columns else ""
    df["cbsa_code"] = zhvi["RegionID"].astype(str) if "RegionID" in zhvi.columns else ""
    df["zhvi_current"] = zhvi[latest_col] if latest_col else None

    if yr_ago_col and latest_col:
        df["price_chg_1yr_pct"] = ((zhvi[latest_col] / zhvi[yr_ago_col]) - 1) * 100
    if five_ago_col and latest_col:
        df["price_chg_5yr_pct"] = ((zhvi[latest_col] / zhvi[five_ago_col]) - 1) * 100

    # Merge rent
    zori = zillow.get("zori_metro")
    if zori is not None:
        zori_cols = [c for c in zori.columns if c[:4].isdigit()]
        zori_latest = zori_cols[-1] if zori_cols else None
        if zori_latest:
            rent_df = zori[["RegionName", zori_latest]].rename(columns={zori_latest: "zori_rent"})
            df = df.merge(rent_df, on="RegionName", how="left")

    # Merge inventory, price cuts, etc
    for name, col_name in [("inventory", "z_inventory"), ("price_cuts", "z_price_cuts_pct"),
                            ("sale_to_list", "z_sale_to_list"), ("new_listings", "z_new_listings")]:
        src = zillow.get(name)
        if src is not None:
            src_cols = [c for c in src.columns if c[:4].isdigit()]
            if src_cols:
                latest = src_cols[-1]
                tmp = src[["RegionName", latest]].rename(columns={latest: col_name})
                df = df.merge(tmp, on="RegionName", how="left")

    # Merge Redfin
    if redfin is not None:
        rf = redfin[redfin["property_type"] == "All Residential"].copy() if "property_type" in redfin.columns else redfin.copy()
        rf_cols = {
            "median_sale_price": "r_median_price",
            "median_ppsf": "r_price_per_sqft",
            "homes_sold": "r_homes_sold",
            "new_listings": "r_new_listings",
            "inventory": "r_inventory",
            "months_of_supply": "r_months_supply",
            "median_dom": "r_median_dom",
            "avg_sale_to_list": "r_sale_to_list",
            "sold_above_list": "r_sold_above_list",
            "price_drops": "r_price_drops",
            "pending_sales": "r_pending_sales",
        }
        for old, new in rf_cols.items():
            if old in rf.columns:
                rf[new] = pd.to_numeric(rf[old], errors="coerce")

        if "region" in rf.columns:
            rf_merge = rf[["region"] + [c for c in rf_cols.values() if c in rf.columns]].copy()
            rf_merge = rf_merge.rename(columns={"region": "RegionName"})
            df = df.merge(rf_merge, on="RegionName", how="left")

    # Merge Census by fuzzy name match (Zillow RegionID != CBSA code)
    if census is not None:
        census_merge = census.copy()
        pop = census_merge["population"]
        census_merge["poverty_rate"] = (census_merge["poverty_count"] / pop * 100).round(1)
        census_merge["bachelors_pct"] = (census_merge["bachelors_count"] / pop * 100).round(1)
        census_merge["homeownership_rate"] = (census_merge["owner_occupied"] / (pop * 0.38) * 100).clip(upper=95).round(1)
        census_merge["pct_wfh"] = (census_merge["wfh"] / census_merge["commuters_total"] * 100).round(1)

        # Parse short name from Census NAME ("Boston-Cambridge-Newton, MA-NH Metro Area" → "Boston")
        census_merge["_join_city"] = census_merge["NAME"].str.split(",").str[0].str.split("-").str[0].str.strip().str.lower()
        census_merge["_join_state"] = census_merge["NAME"].str.extract(r",\s*([A-Z]{2})")[0]

        # Parse short name from Zillow ("Chicago, IL" → "chicago")
        df["_join_city"] = df["RegionName"].str.split(",").str[0].str.split("-").str[0].str.strip().str.lower()
        df["_join_state"] = df["RegionName"].str.extract(r",\s*([A-Z]{2})")[0]

        keep = ["_join_city", "_join_state", "median_hh_income", "median_rent_census", "population",
                "median_home_value_census", "median_age", "poverty_rate", "bachelors_pct",
                "homeownership_rate", "pct_wfh"]
        census_merge = census_merge[[c for c in keep if c in census_merge.columns]]

        df = df.merge(census_merge, on=["_join_city", "_join_state"], how="left", suffixes=("", "_census"))
        df = df.drop(columns=["_join_city", "_join_state"], errors="ignore")
        matched = df["population"].notna().sum()
        log("Census", "OK", f"Matched {matched}/{len(df)} metros by name")

    # Derived metrics
    if mortgage_rate and "zhvi_current" in df.columns and "median_hh_income" in df.columns:
        monthly_rate = (mortgage_rate / 100) / 12
        n_payments = 360
        loan = df["zhvi_current"] * 0.8  # 20% down
        df["monthly_payment"] = (loan * monthly_rate * (1 + monthly_rate)**n_payments / ((1 + monthly_rate)**n_payments - 1)).round(0)
        df["payment_pct_income"] = (df["monthly_payment"] / (df["median_hh_income"] / 12) * 100).round(1)

    if "zhvi_current" in df.columns and "median_hh_income" in df.columns:
        df["price_to_income"] = (df["zhvi_current"] / df["median_hh_income"]).round(2)

    if "zhvi_current" in df.columns and "zori_rent" in df.columns:
        df["price_to_rent"] = (df["zhvi_current"] / (df["zori_rent"] * 12)).round(2)
        df["payment_vs_rent"] = (df["monthly_payment"] - df["zori_rent"]).round(0) if "monthly_payment" in df.columns else None
        df["gross_rental_yield"] = (df["zori_rent"] * 12 / df["zhvi_current"] * 100).round(2)

    # Parse state abbreviation
    if "StateName" in df.columns:
        df["state_abbr"] = df["StateName"].str.strip()

    # Drop national aggregate and rows without a home price
    df = df[df["RegionName"] != "United States"]
    df = df.dropna(subset=["zhvi_current"]).reset_index(drop=True)

    log("Build", "OK", f"{len(df)} metros, {len(df.columns)} columns")
    return df


# ═══════════════════════════════════════════
# 6. GEOCODE + EXPORT
# ═══════════════════════════════════════════
def geocode_and_export(df):
    print("\n=== Geocoding ===")
    try:
        cities = pd.read_csv(COORDS_URL)
        city_lookup = {}
        for _, r in cities.iterrows():
            key = (r["CITY"].strip().lower(), r["STATE_CODE"].strip())
            city_lookup[key] = (r["LATITUDE"], r["LONGITUDE"])

        matched = 0
        for i, row in df.iterrows():
            city = row["RegionName"].split(",")[0].split("-")[0].strip().lower()
            state = row.get("state_abbr", "")
            key = (city, state)
            if key in city_lookup:
                df.at[i, "_lat"] = city_lookup[key][0]
                df.at[i, "_lon"] = city_lookup[key][1]
                matched += 1
        log("Geocode", "OK", f"{matched}/{len(df)} metros matched")
    except Exception as e:
        log("Geocode", "FAIL", str(e))

    # Round floats
    for c in df.select_dtypes(include="float").columns:
        df[c] = df[c].round(2)

    # Export to JSON (NaN → null)
    records = json.loads(df.to_json(orient="records"))
    with open(OUT, "w") as f:
        json.dump(records, f, separators=(",", ":"))

    size_kb = OUT.stat().st_size / 1024
    log("Export", "OK", f"{len(records)} metros → {OUT.name} ({size_kb:.0f} KB)")

    # Save historical snapshot
    history_dir = ROOT / "history"
    history_dir.mkdir(exist_ok=True)
    from datetime import date
    snapshot = history_dir / f"{date.today().isoformat()}.json"
    with open(snapshot, "w") as f:
        json.dump(records, f, separators=(",", ":"))
    log("History", "OK", f"Snapshot saved: {snapshot.name}")


# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════
def main():
    print("=" * 60)
    print("HOUSING MARKET DATA REFRESH")
    print("=" * 60)
    print(f"FRED key: {'set' if FRED_KEY else 'MISSING'}")
    print(f"Census key: {'set' if CENSUS_KEY else 'MISSING'}")
    print(f"BEA key: {'set' if BEA_KEY else 'MISSING'}")

    zillow = pull_zillow()
    time.sleep(2)
    redfin = pull_redfin()
    time.sleep(2)
    mortgage_rate = pull_fred()
    time.sleep(2)
    census = pull_census()

    df = build_dataset(zillow, redfin, mortgage_rate, census)
    if df is not None:
        geocode_and_export(df)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
