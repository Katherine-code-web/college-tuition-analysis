"""
ROI / CP Value calculation functions
"""

import pandas as pd
import numpy as np


def compute_value_score(earnings_10yr, net_price, completion_rate=None) -> float | None:
    """
    Value Score = 10-year median earnings / annual net price.

    Optionally weighted by completion rate (probability-adjusted ROI).
    Higher is better.

    Returns None if required inputs are missing.
    """
    if not earnings_10yr or not net_price or net_price == 0:
        return None
    score = earnings_10yr / net_price
    if completion_rate and completion_rate > 0:
        score *= completion_rate  # Penalizes schools where most students don't finish
    return round(score, 2)


def compute_debt_to_income(median_debt, earnings_10yr) -> float | None:
    """
    Debt-to-Income = median debt at graduation / 10-year earnings.

    Below 1.0 is generally manageable. Above 1.5 is a warning sign.
    Returns None if inputs are missing.
    """
    if not median_debt or not earnings_10yr or earnings_10yr == 0:
        return None
    return round(median_debt / earnings_10yr, 2)


def compute_payback_years(net_price, earnings_10yr, years=4) -> float | None:
    """
    Estimate how many years of post-grad earnings cover total tuition cost.

    payback_years = (net_price × years) / earnings_10yr
    """
    if not net_price or not earnings_10yr or earnings_10yr == 0:
        return None
    total_cost = net_price * years
    return round(total_cost / earnings_10yr, 1)


def enrich_df(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed ROI metrics to a school DataFrame."""
    df = df.copy()
    df["value_score"] = df.apply(
        lambda r: compute_value_score(r["earnings_10yr"], r["net_price"], r["completion_rate"]),
        axis=1,
    )
    df["debt_to_income"] = df.apply(
        lambda r: compute_debt_to_income(r["median_debt"], r["earnings_10yr"]),
        axis=1,
    )
    df["payback_years"] = df.apply(
        lambda r: compute_payback_years(r["net_price"], r["earnings_10yr"]),
        axis=1,
    )
    return df


def score_label(score: float | None, lang: str = "en") -> str:
    """Return a human-readable label for a value score."""
    if score is None:
        return "N/A"
    labels = {
        "en": {(0, 2): "Low", (2, 4): "Fair", (4, 6): "Good", (6, 999): "Excellent"},
        "zh": {(0, 2): "偏低", (2, 4): "普通", (4, 6): "良好", (6, 999): "優秀"},
    }
    for (lo, hi), label in labels.get(lang, labels["en"]).items():
        if lo <= score < hi:
            return label
    return "N/A"


def debt_label(ratio: float | None, lang: str = "en") -> str:
    """Return a traffic-light label for debt-to-income ratio."""
    if ratio is None:
        return "N/A"
    if lang == "zh":
        if ratio < 0.5:
            return "🟢 低負擔"
        elif ratio < 1.0:
            return "🟡 可負擔"
        elif ratio < 1.5:
            return "🟠 注意"
        else:
            return "🔴 高負擔"
    else:
        if ratio < 0.5:
            return "🟢 Low"
        elif ratio < 1.0:
            return "🟡 Manageable"
        elif ratio < 1.5:
            return "🟠 Caution"
        else:
            return "🔴 High Risk"
