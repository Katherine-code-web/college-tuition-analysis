"""
Three-layer earnings fallback system for Smart Matcher.

When College Scorecard field-of-study earnings are privacy-suppressed
(common for graduate cohorts), this module provides national-level estimates.

Layer 1 — College Scorecard program-level  (handled in Smart Matcher directly)
Layer 2a — Program starting salary CSV     (school + program specific medians)
Layer 2b — ACS PUMS field-level            (national Master's median by field)
Layer 3 — BLS OEWS occupation-level        (CSV from scripts/build_bls_earnings_table.py)

⚠️  Layer 2b figures are estimated from ACS + Georgetown CEW published data.
    They reflect the NATIONAL median for Master's holders in each field,
    not the outcome at any specific school.  A Harvard MBA vs. a random MBA
    will have very different actual outcomes.

⚠️  Layer 3 figures (BLS) cover ALL education levels, so they underestimate
    earnings for Master's / PhD holders and overestimate for some fields.

Data last updated: April 2025.  TODO: refresh from ACS API annually.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

_DATA_DIR = Path(__file__).parent.parent / "data"

# Mapping from College Scorecard CIP 2-digit prefix + degree → program label
# used to look up rows in program_starting_salary.csv
_CIP_DEGREE_TO_PROGRAM: dict[tuple[str, str], list[str]] = {
    ("11", "Master's"): ["Computer Science (MS)", "Data Science (MS)"],
    ("11", "MBA"):      ["Business Analytics (MS)"],
    ("14", "Master's"): ["Electrical & Computer Engineering (MS)"],
    ("52", "MBA"):      ["MBA", "Business Analytics (MS)", "Finance (MS)"],
    ("52", "Master's"): ["Business Analytics (MS)", "Finance (MS)"],
    ("22", "Law (JD)"): ["Law (JD)"],
    ("22", "Doctoral"): ["Law (JD)"],
    ("27", "Master's"): ["Data Science (MS)"],
    ("30", "Master's"): ["Data Science (MS)"],
    ("45", "Master's"): ["Data Science (MS)"],
}


# ── Cached loaders ────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_program_salaries() -> pd.DataFrame:
    path = _DATA_DIR / "program_starting_salary.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"unitid": str})
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def _load_acs_earnings() -> pd.DataFrame:
    path = _DATA_DIR / "masters_earnings_by_field.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"FOD1P": str, "cip_2digit": str})
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def _load_bls_earnings() -> pd.DataFrame:
    path = _DATA_DIR / "bls_earnings_by_cip.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"CIP_2DIGIT": str})
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def _load_fod_mapping() -> pd.DataFrame:
    path = _DATA_DIR / "fod1p_to_cip_mapping.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"FOD1P": str, "cip_2digit": str})
    return pd.DataFrame()


# ── Public API ────────────────────────────────────────────────────────────────

def get_program_salary(
    school_name: str,
    unitid: int | str | None,
    cip_2digit: str,
    credential_level: str,
) -> int | None:
    """
    Look up a school-specific program starting salary from program_starting_salary.csv.

    Tries to match by unitid first (exact), then by school_name (case-insensitive
    partial match). Returns the median_starting_salary as an int, or None if no
    match is found.
    """
    df = _load_program_salaries()
    if df.empty:
        return None

    # Determine which program labels to search for this CIP + degree combo
    prog_labels = _CIP_DEGREE_TO_PROGRAM.get((str(cip_2digit).zfill(2), credential_level), [])
    if not prog_labels:
        # Fallback: try just the credential level as a suffix match
        prog_labels = [p for p in df["program"].unique() if credential_level in p]
    if not prog_labels:
        return None

    subset = df[df["program"].isin(prog_labels)]
    if subset.empty:
        return None

    # Try exact unitid match first
    if unitid is not None:
        try:
            uid_str = str(int(unitid))
            id_match = subset[subset["unitid"] == uid_str]
            if not id_match.empty:
                return int(id_match["median_starting_salary"].iloc[0])
        except (ValueError, TypeError):
            pass

    # Fuzzy name match: check if school_name appears in CSV name or vice versa
    if school_name:
        name_lower = school_name.lower()
        name_match = subset[
            subset["school_name"].str.lower().str.contains(name_lower[:30], regex=False, na=False)
            | subset["school_name"].str.lower().apply(lambda n: n[:30] in name_lower)
        ]
        if not name_match.empty:
            return int(name_match["median_starting_salary"].iloc[0])

    return None


CONFIDENCE_LEVELS = ("program", "field_national", "occupation", "institution")

CONFIDENCE_BADGES = {
    "program":        "🟢",
    "field_national": "🟡",
    "occupation":     "🟠",
    "institution":    "🔴",
}

CONFIDENCE_LABELS = {
    "en": {
        "program":        "Program data",
        "field_national": "National estimate",
        "occupation":     "Occupation-based",
        "institution":    "School-wide",
    },
    "zh": {
        "program":        "課程資料",
        "field_national": "全國估算",
        "occupation":     "職業薪資",
        "institution":    "學校整體",
    },
}


def get_field_earnings(
    cip_2digit: str,
    credential_level: str = "Master's",
) -> dict:
    """
    Return a national-level earnings estimate for a given CIP 2-digit field
    and credential level.

    Returns a dict with keys:
        median        — int | None
        p25           — int | None
        p75           — int | None
        source        — str  ("acs_pums", "bls_oews", or "unavailable")
        confidence    — str  ("field_national", "occupation", or "none")
        note_en       — str  human-readable caveat (English)
        note_zh       — str  human-readable caveat (Chinese)
    """
    cip_2digit = str(cip_2digit).zfill(2)

    # ── Layer 2: ACS PUMS field-level lookup ──────────────────────────────────
    if credential_level in ("Master's", "MBA", "Doctoral"):
        acs = _load_acs_earnings()
        fod_map = _load_fod_mapping()

        if not acs.empty and not fod_map.empty:
            # Find FOD1P codes that map to this CIP 2-digit
            matching_fods = fod_map.loc[
                fod_map["cip_2digit"] == cip_2digit, "FOD1P"
            ].astype(str).tolist()

            if matching_fods:
                rows = acs[acs["FOD1P"].astype(str).isin(matching_fods)]
                if not rows.empty:
                    median = int(rows["median_annual_earnings"].median())
                    p25 = int(rows["p25_earnings"].median())
                    p75 = int(rows["p75_earnings"].median())
                    year = int(rows["year"].max()) if "year" in rows.columns else 2023
                    return {
                        "median":     median,
                        "p25":        p25,
                        "p75":        p75,
                        "source":     "acs_pums",
                        "confidence": "field_national",
                        "note_en": (
                            f"National median for Master's degree holders in this field "
                            f"(ACS + Georgetown CEW, {year}). "
                            "Not school-specific — top programs typically exceed this."
                        ),
                        "note_zh": (
                            f"全國持該領域碩士學位者的薪資中位數（ACS + Georgetown CEW, {year}）。"
                            "非特定學校數據 — 頂尖課程的實際薪資通常高於此值。"
                        ),
                    }

    # ── Layer 3: BLS OEWS occupation-level ────────────────────────────────────
    bls = _load_bls_earnings()
    if not bls.empty:
        row = bls[bls["CIP_2DIGIT"] == cip_2digit]
        if not row.empty:
            r = row.iloc[0]
            med = r.get("bls_median_salary")
            if pd.notna(med):
                return {
                    "median":     int(med),
                    "p25":        int(r["bls_p25_salary"]) if pd.notna(r.get("bls_p25_salary")) else None,
                    "p75":        int(r["bls_p75_salary"]) if pd.notna(r.get("bls_p75_salary")) else None,
                    "source":     "bls_oews",
                    "confidence": "occupation",
                    "note_en": (
                        "Based on typical occupations for this field (BLS OEWS). "
                        "Includes all education levels — may underestimate Master's earnings."
                    ),
                    "note_zh": (
                        "依據該領域典型職業薪資（BLS OEWS）。"
                        "涵蓋所有學歷，可能低估碩士畢業生的薪資。"
                    ),
                }

    # ── No data ───────────────────────────────────────────────────────────────
    return {
        "median":     None,
        "p25":        None,
        "p75":        None,
        "source":     "unavailable",
        "confidence": "none",
        "note_en":    "No national earnings estimate available for this field.",
        "note_zh":    "此領域暫無全國薪資估算資料。",
    }


def earnings_confidence_html(confidence: str, lang: str = "en") -> str:
    """Return a small HTML badge for the earnings confidence level."""
    badge = CONFIDENCE_BADGES.get(confidence, "⚪")
    label = CONFIDENCE_LABELS.get(lang, CONFIDENCE_LABELS["en"]).get(confidence, confidence)
    colors = {
        "program":        ("#DDFAE4", "#2E7D32"),
        "field_national": ("#FFFDE7", "#F57F17"),
        "occupation":     ("#FFF3E0", "#E65100"),
        "institution":    ("#FFEBEE", "#B71C1C"),
    }
    bg, fg = colors.get(confidence, ("#F5F5F5", "#555"))
    return (
        f'<span style="background:{bg};color:{fg};border:1.5px solid {fg};'
        f'border-radius:12px;padding:2px 8px;font-size:0.72rem;font-weight:800;">'
        f'{badge} {label}</span>'
    )
