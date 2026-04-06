"""
College Scorecard API wrapper
U.S. Department of Education — https://collegescorecard.ed.gov/data/documentation/
"""

import os
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.data.gov/ed/collegescorecard/v1/schools"

# Fields to request from the API
FIELDS = ",".join([
    "id",
    "school.name",
    "school.state",
    "school.city",
    "school.ownership",
    "school.school_url",
    "school.price_calculator_url",
    "school.financial_aid_url",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.avg_net_price.public",
    "latest.cost.avg_net_price.private",
    "latest.earnings.10_yrs_after_entry.median",
    "latest.earnings.6_yrs_after_entry.median",
    "latest.aid.median_debt.completers.overall",
    "latest.aid.pell_grant_rate",
    "latest.aid.federal_loan_rate",
    "latest.completion.rate_suppressed.overall",
    "latest.student.size",
    "latest.admissions.admission_rate.overall",
    "latest.admissions.sat_scores.average.overall",
])

OWNERSHIP_MAP = {1: "Public", 2: "Private Nonprofit", 3: "Private For-Profit"}
OWNERSHIP_MAP_ZH = {1: "公立", 2: "私立非營利", 3: "私立營利"}


def get_api_key() -> str:
    key = os.getenv("COLLEGE_SCORECARD_API_KEY", "")
    if not key or key == "your_api_key_here":
        st.error(
            "API key not found. Please create a `.env` file with your "
            "`COLLEGE_SCORECARD_API_KEY`. Get a free key at https://api.data.gov/signup/"
        )
        st.stop()
    return key


@st.cache_data(ttl=3600, show_spinner=False)
def search_schools(
    name: str = "",
    state: str = "",
    ownership: int = 0,
    min_size: int = 0,
    max_size: int = 9_999_999,
    per_page: int = 25,
    page: int = 0,
) -> tuple[list[dict], int]:
    """
    Search schools via College Scorecard API.

    Returns (results_list, total_count).
    """
    params: dict = {
        "api_key": get_api_key(),
        "fields": FIELDS,
        "per_page": per_page,
        "page": page,
        "latest.student.size__range": f"{min_size}..{max_size}",
        "_sort": "latest.completion.rate_suppressed.overall:desc",
    }
    if name:
        params["school.name"] = name
    if state and state not in ("All", ""):
        params["school.state"] = state
    if ownership:
        params["school.ownership"] = ownership

    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", []), data.get("metadata", {}).get("total", 0)
    except requests.RequestException as e:
        st.error(f"API request failed: {e}")
        return [], 0


@st.cache_data(ttl=3600, show_spinner=False)
def get_school_by_id(school_id: int) -> dict | None:
    """Fetch a single school's data by its IPEDS ID."""
    params = {"api_key": get_api_key(), "fields": FIELDS, "id": school_id}
    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return results[0] if results else None
    except requests.RequestException:
        return None


def results_to_df(results: list[dict]) -> pd.DataFrame:
    """Flatten API result dicts into a tidy DataFrame."""
    rows = []
    for r in results:
        ownership_code = r.get("school.ownership")
        # Net price differs by school type in the API
        net_price = (
            r.get("latest.cost.avg_net_price.public")
            if ownership_code == 1
            else r.get("latest.cost.avg_net_price.private")
        )
        rows.append({
            "id": r.get("id"),
            "name": r.get("school.name"),
            "state": r.get("school.state"),
            "city": r.get("school.city"),
            "ownership_code": ownership_code,
            "type_en": OWNERSHIP_MAP.get(ownership_code, "Unknown"),
            "type_zh": OWNERSHIP_MAP_ZH.get(ownership_code, "未知"),
            "url": r.get("school.school_url"),
            "npc_url": r.get("school.price_calculator_url"),
            "aid_url": r.get("school.financial_aid_url"),
            "tuition_in": r.get("latest.cost.tuition.in_state"),
            "tuition_out": r.get("latest.cost.tuition.out_of_state"),
            "net_price": net_price,
            "earnings_10yr": r.get("latest.earnings.10_yrs_after_entry.median"),
            "earnings_6yr": r.get("latest.earnings.6_yrs_after_entry.median"),
            "median_debt": r.get("latest.aid.median_debt.completers.overall"),
            "pell_rate": r.get("latest.aid.pell_grant_rate"),
            "loan_rate": r.get("latest.aid.federal_loan_rate"),
            "completion_rate": r.get("latest.completion.rate_suppressed.overall"),
            "enrollment": r.get("latest.student.size"),
            "admission_rate": r.get("latest.admissions.admission_rate.overall"),
            "sat_avg": r.get("latest.admissions.sat_scores.average.overall"),
        })
    return pd.DataFrame(rows)


def fmt_usd(value, na="N/A") -> str:
    """Format a number as USD string."""
    if value is None or pd.isna(value):
        return na
    return f"${value:,.0f}"


def fmt_pct(value, na="N/A") -> str:
    """Format a 0-1 float as percentage string."""
    if value is None or pd.isna(value):
        return na
    return f"{value * 100:.1f}%"
