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

# Common abbreviations that don't match API school names directly
SCHOOL_ALIASES = {
    "mit": "Massachusetts Institute of Technology",
    "ucla": "University of California-Los Angeles",
    "ucsd": "University of California-San Diego",
    "ucsb": "University of California-Santa Barbara",
    "usc": "University of Southern California",
    "nyu": "New York University",
    "bu": "Boston University",
    "neu": "Northeastern University",
    "bc": "Boston College",
    "cmu": "Carnegie Mellon",
    "gatech": "Georgia Institute of Technology",
    "gt": "Georgia Institute of Technology",
    "uw": "University of Washington-Seattle",
    "uiuc": "University of Illinois Urbana-Champaign",
    "umich": "University of Michigan-Ann Arbor",
    "unc": "University of North Carolina at Chapel Hill",
    "vt": "Virginia Polytechnic",
    "pitt": "University of Pittsburgh",
    "tamu": "Texas A&M University-College Station",
    "osu": "Ohio State University-Main Campus",
    "uva": "University of Virginia-Main Campus",
    "wustl": "Washington University in St Louis",
    "upenn": "University of Pennsylvania",
    "caltech": "California Institute of Technology",
    # Common misspellings
    "havard": "Harvard University",
    "harvad": "Harvard University",
    "harverd": "Harvard University",
    "stanfod": "Stanford University",
    "standford": "Stanford University",
    "priinceton": "Princeton University",
    "princton": "Princeton University",
    "columiba": "Columbia University",
    "berkley": "University of California-Berkeley",
    "berkely": "University of California-Berkeley",
    "cornnel": "Cornell University",
    "yael": "Yale University",
    "pensylvania": "University of Pennsylvania",
    "carnegi": "Carnegie Mellon University",
    "chicgo": "University of Chicago",
    "notredam": "University of Notre Dame",
    "vandrebilt": "Vanderbilt University",
    "geortown": "Georgetown University",
    "michagan": "University of Michigan-Ann Arbor",
    "notheastern": "Northeastern University",
    "northeasten": "Northeastern University",
    # Chinese aliases
    "麻省理工": "Massachusetts Institute of Technology",
    "哈佛": "Harvard",
    "耶魯": "Yale",
    "史丹佛": "Stanford",
    "普林斯頓": "Princeton",
    "哥倫比亞": "Columbia",
    "康乃爾": "Cornell",
    "賓大": "University of Pennsylvania",
    "卡內基美隆": "Carnegie Mellon",
    "波士頓大學": "Boston University",
    "東北大學": "Northeastern University",
    "南加大": "University of Southern California",
    "紐約大學": "New York University",
}


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
        # Resolve common abbreviations and Chinese aliases
        resolved = SCHOOL_ALIASES.get(name.lower().strip(), name)
        params["school.name"] = resolved
    if state and state not in ("All", ""):
        params["school.state"] = state
    if ownership:
        params["school.ownership"] = ownership

    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        total = data.get("metadata", {}).get("total", 0)

        # If no results and a name was given, try fuzzy fallback:
        # strip last char (catches 1-char typos at end like "Havard" → "Harar" → skip,
        # better: try without last char progressively)
        if not results and name and len(name) >= 5:
            fallback_name = SCHOOL_ALIASES.get(name[:-1].lower().strip())
            if not fallback_name:
                # Try dropping last character as fuzzy match
                fallback_params = dict(params)
                fallback_params["school.name"] = name[:-1]
                try:
                    fb_resp = requests.get(API_BASE, params=fallback_params, timeout=15)
                    fb_data = fb_resp.json()
                    results = fb_data.get("results", [])
                    total = fb_data.get("metadata", {}).get("total", 0)
                except Exception:
                    pass

        return results, total
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


# Fields for program-level (CIP 4-digit) data
PROGRAM_FIELDS = "id,school.name,latest.programs.cip_4_digit"


@st.cache_data(ttl=3600, show_spinner=False)
def get_school_programs(school_id: int) -> list[dict]:
    """
    Fetch field-of-study (CIP 4-digit) programs for a school.

    Returns a list of dicts with keys:
      cip_code, cip_title, cred_level, cred_title,
      median_earnings, median_debt
    """
    params = {
        "api_key": get_api_key(),
        "fields": PROGRAM_FIELDS,
        "id": school_id,
    }
    try:
        resp = requests.get(API_BASE, params=params, timeout=15)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return []
        raw_programs = results[0].get("latest.programs.cip_4_digit") or []
        if not isinstance(raw_programs, list):
            return []
        programs = []
        for p in raw_programs:
            if not isinstance(p, dict):
                continue
            code = p.get("code")
            if code is None:
                continue
            cred = p.get("credential") or {}
            earn = p.get("earnings") or {}
            debt = p.get("debt") or {}
            median_earn = earn.get("median_earnings")
            median_debt_val = debt.get("median_loan_debt")
            # Skip suppressed / missing data rows
            if median_earn == "PrivacySuppressed":
                median_earn = None
            if median_debt_val == "PrivacySuppressed":
                median_debt_val = None
            programs.append({
                "cip_code": str(code).zfill(4),
                "cip_title": p.get("title", ""),
                "cred_level": cred.get("level"),
                "cred_title": cred.get("title", ""),
                "median_earnings": int(median_earn) if median_earn else None,
                "median_debt": int(median_debt_val) if median_debt_val else None,
            })
        return programs
    except requests.RequestException as e:
        return []


# ── Matcher-specific fields (includes SAT/ACT percentiles) ────────────────────
MATCHER_FIELDS = FIELDS + "," + ",".join([
    "latest.admissions.sat_scores.25th_percentile.math",
    "latest.admissions.sat_scores.75th_percentile.math",
    "latest.admissions.sat_scores.25th_percentile.critical_reading",
    "latest.admissions.sat_scores.75th_percentile.critical_reading",
    "latest.admissions.act_scores.25th_percentile.cumulative",
    "latest.admissions.act_scores.75th_percentile.cumulative",
])


def matcher_result_to_row(r: dict) -> dict:
    """Like results_to_df rows but also extracts SAT/ACT percentile fields."""
    ownership_code = r.get("school.ownership")
    net_price = (
        r.get("latest.cost.avg_net_price.public")
        if ownership_code == 1
        else r.get("latest.cost.avg_net_price.private")
    )
    sat_m25 = r.get("latest.admissions.sat_scores.25th_percentile.math") or 0
    sat_m75 = r.get("latest.admissions.sat_scores.75th_percentile.math") or 0
    sat_v25 = r.get("latest.admissions.sat_scores.25th_percentile.critical_reading") or 0
    sat_v75 = r.get("latest.admissions.sat_scores.75th_percentile.critical_reading") or 0
    return {
        "id": r.get("id"),
        "name": r.get("school.name"),
        "state": r.get("school.state"),
        "city": r.get("school.city"),
        "ownership_code": ownership_code,
        "type_en": OWNERSHIP_MAP.get(ownership_code, "Unknown"),
        "type_zh": OWNERSHIP_MAP_ZH.get(ownership_code, "未知"),
        "url": r.get("school.school_url"),
        "tuition_in": r.get("latest.cost.tuition.in_state"),
        "tuition_out": r.get("latest.cost.tuition.out_of_state"),
        "net_price": net_price,
        "earnings_10yr": r.get("latest.earnings.10_yrs_after_entry.median"),
        "earnings_6yr": r.get("latest.earnings.6_yrs_after_entry.median"),
        "median_debt": r.get("latest.aid.median_debt.completers.overall"),
        "pell_rate": r.get("latest.aid.pell_grant_rate"),
        "completion_rate": r.get("latest.completion.rate_suppressed.overall"),
        "enrollment": r.get("latest.student.size"),
        "admission_rate": r.get("latest.admissions.admission_rate.overall"),
        "sat_avg": r.get("latest.admissions.sat_scores.average.overall"),
        "sat_p25": (sat_v25 + sat_m25) if (sat_v25 and sat_m25) else None,
        "sat_p75": (sat_v75 + sat_m75) if (sat_v75 and sat_m75) else None,
        "act_p25": r.get("latest.admissions.act_scores.25th_percentile.cumulative"),
        "act_p75": r.get("latest.admissions.act_scores.75th_percentile.cumulative"),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_candidate_schools(
    states: tuple[str, ...] = (),
    ownership: int = 0,
    cip_2digit: str = "",
    per_page: int = 100,
    n_pages: int = 2,
) -> list[dict]:
    """
    Fetch a large batch of schools for Smart Matcher scoring.
    Uses MATCHER_FIELDS so SAT/ACT percentile data is included.

    cip_2digit: 2-digit CIP prefix (e.g. "22" for Law, "51" for Medicine).
    When provided, filters the API to schools that offer programs in that CIP range.
    """
    all_results: list[dict] = []

    for page_num in range(n_pages):
        params: dict = {
            "api_key": get_api_key(),
            "fields": MATCHER_FIELDS,
            "per_page": per_page,
            "page": page_num,
            "_sort": "latest.completion.rate_suppressed.overall:desc",
            "latest.student.size__range": "200..",
        }
        if states:
            params["school.state"] = ",".join(states)
        if ownership:
            params["school.ownership"] = ownership
        if cip_2digit:
            # Filter to schools that offer programs in this CIP 2-digit category.
            # College Scorecard stores 4-digit codes, so CIP "22" maps to 2200..2299.
            lo = int(cip_2digit) * 100
            hi = lo + 99
            params["latest.programs.cip_4_digit.code__range"] = f"{lo}..{hi}"

        try:
            resp = requests.get(API_BASE, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            total = data.get("metadata", {}).get("total", 0)
            all_results.extend(results)
            if len(all_results) >= total:
                break
        except requests.RequestException:
            break

    return all_results


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
