"""
One-time script: build data/masters_earnings_by_field.csv from Census ACS PUMS.

Run once (or annually to refresh):
    python scripts/build_acs_earnings_table.py

Requires:
    pip install requests pandas numpy

Optional: set CENSUS_API_KEY environment variable for a higher rate limit.
Free key signup: https://api.census.gov/data/key_signup.html

The script tries Method A (Census API microdata) first.  If that fails or
returns fewer than 20 fields, it falls back to Method B (the hardcoded table
already committed in data/masters_earnings_by_field.csv).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests

API_KEY = os.getenv("CENSUS_API_KEY", "")
BASE_URL = "https://api.census.gov/data/2023/acs/acs1/pums"
OUT_PATH = Path(__file__).parent.parent / "data" / "masters_earnings_by_field.csv"
FOD_MAP_PATH = Path(__file__).parent.parent / "data" / "fod1p_to_cip_mapping.csv"


# ── Weighted median helper ─────────────────────────────────────────────────────

def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """Compute a weighted quantile (0 < q < 1)."""
    sorted_idx = np.argsort(values)
    vals = values[sorted_idx]
    wts = weights[sorted_idx]
    cumsum = wts.cumsum()
    threshold = cumsum[-1] * q
    return float(vals[(cumsum >= threshold).argmax()])


# ── Method A: Census PUMS API ──────────────────────────────────────────────────

def fetch_from_census_api() -> pd.DataFrame | None:
    """
    Pull ACS 2023 1-Year PUMS microdata via the Census API and compute
    weighted earnings statistics by FOD1P for Master's degree holders (SCHL=22).

    Returns None on failure.
    """
    params = {
        "get": "FOD1P,WAGP,PWGTP",
        "for": "state:*",
        "SCHL": "22",  # Master's degree
    }
    if API_KEY:
        params["key"] = API_KEY

    print("Fetching from Census API…")
    try:
        resp = requests.get(BASE_URL, params=params, timeout=300)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"Census API failed: {exc}")
        return None

    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)

    df["WAGP"] = pd.to_numeric(df["WAGP"], errors="coerce")
    df["PWGTP"] = pd.to_numeric(df["PWGTP"], errors="coerce")
    df["FOD1P"] = df["FOD1P"].astype(str)

    # Filter: employed with wages > 0
    df = df[(df["WAGP"] > 0) & df["WAGP"].notna() & df["PWGTP"].notna()]

    if df.empty or df["FOD1P"].nunique() < 10:
        print("Census API returned insufficient data")
        return None

    print(f"API returned {len(df):,} records across {df['FOD1P'].nunique()} fields")

    results = []
    for fod, group in df.groupby("FOD1P"):
        wages = group["WAGP"].values.astype(float)
        weights = group["PWGTP"].values.astype(float)
        results.append({
            "FOD1P": fod,
            "median_annual_earnings": int(weighted_quantile(wages, weights, 0.50)),
            "p25_earnings":           int(weighted_quantile(wages, weights, 0.25)),
            "p75_earnings":           int(weighted_quantile(wages, weights, 0.75)),
            "weighted_count":         int(weights.sum()),
            "sample_count":           len(group),
            "source":                 "ACS PUMS 2023",
            "year":                   2023,
        })

    return pd.DataFrame(results)


# ── Combine with FOD→CIP mapping ──────────────────────────────────────────────

def enrich_with_mapping(df: pd.DataFrame) -> pd.DataFrame:
    fod_map = pd.read_csv(FOD_MAP_PATH, dtype={"FOD1P": str, "cip_2digit": str})
    merged = df.merge(fod_map[["FOD1P", "fod_name", "cip_2digit"]], on="FOD1P", how="left")
    merged["field_name"] = merged["fod_name"]
    merged["sample_size"] = merged["sample_count"].apply(
        lambda n: "large" if n >= 500 else ("medium" if n >= 100 else "small")
    )
    return merged


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    result = fetch_from_census_api()

    if result is None or len(result) < 20:
        print("Method A failed or insufficient. Using existing hardcoded table.")
        if OUT_PATH.exists():
            print(f"Existing table at {OUT_PATH} is retained.")
        else:
            print("ERROR: No existing table found. Commit data/masters_earnings_by_field.csv first.")
        sys.exit(0)

    result = enrich_with_mapping(result)

    cols_order = [
        "FOD1P", "field_name", "cip_2digit",
        "median_annual_earnings", "p25_earnings", "p75_earnings",
        "sample_size", "source", "year",
    ]
    for c in cols_order:
        if c not in result.columns:
            result[c] = None
    result[cols_order].to_csv(OUT_PATH, index=False)
    print(f"Saved {len(result)} fields to {OUT_PATH}")


if __name__ == "__main__":
    main()
