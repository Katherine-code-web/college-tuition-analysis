"""
Matching utilities for Smart School Matcher.

Admission probability estimates are rough approximations based on publicly
available score distributions only. They do NOT account for essays,
recommendations, demographics, yield management, or holistic review.
"""

import pandas as pd


# ── Admission Probability ──────────────────────────────────────────────────────

def estimate_admission_probability(
    user_profile: dict, school: dict
) -> tuple[float | None, bool]:
    """
    Estimate admission probability for a user at a given school.
    Returns (probability_0_to_1, has_score_data).
    """
    base_rate = school.get("admission_rate")
    if base_rate is None or base_rate <= 0:
        return None, False

    score_factor = 1.0
    has_score_data = False

    user_sat = user_profile.get("sat")
    sat_p25 = school.get("sat_p25")
    sat_p75 = school.get("sat_p75")

    if user_sat and sat_p25 and sat_p75:
        has_score_data = True
        mid = (sat_p25 + sat_p75) / 2
        if user_sat >= sat_p75:
            score_factor = 1.8
        elif user_sat >= mid:
            score_factor = 1.3
        elif user_sat >= sat_p25:
            score_factor = 1.0
        else:
            score_factor = 0.5
    else:
        user_act = user_profile.get("act")
        act_p25 = school.get("act_p25")
        act_p75 = school.get("act_p75")
        if user_act and act_p25 and act_p75:
            has_score_data = True
            mid = (act_p25 + act_p75) / 2
            if user_act >= act_p75:
                score_factor = 1.8
            elif user_act >= mid:
                score_factor = 1.3
            elif user_act >= act_p25:
                score_factor = 1.0
            else:
                score_factor = 0.5

    user_gpa = user_profile.get("gpa")
    if user_gpa:
        if user_gpa >= 3.9:
            score_factor *= 1.2
        elif user_gpa >= 3.5:
            score_factor *= 1.05
        elif user_gpa >= 3.0:
            score_factor *= 0.90
        elif user_gpa >= 2.5:
            score_factor *= 0.70
        else:
            score_factor *= 0.50

    prob = round(min(base_rate * score_factor, 0.95), 3)
    return prob, has_score_data


def classify_school(prob: float | None) -> str:
    """Classify as Reach / Target / Safety."""
    if prob is None:
        return "Unknown"
    if prob < 0.25:
        return "Reach"
    elif prob < 0.60:
        return "Target"
    else:
        return "Safety"


# ── Budget Fit ─────────────────────────────────────────────────────────────────

def get_budget_fit(user_profile: dict, school: dict) -> tuple[str, str]:
    """Returns (display_text, color_hex) for budget fit indicator."""
    is_intl = user_profile.get("nationality", "United States") != "United States"
    cost = (school.get("tuition_out") if is_intl else None) or school.get("net_price")
    budget = user_profile.get("annual_budget") or 50000

    if cost is None or (isinstance(cost, float) and pd.isna(cost)):
        return "❓ Cost data unavailable", "#9E9E9E"

    cost = int(cost)
    budget = int(budget)

    if cost <= budget:
        return f"✅ Fits ${budget:,} budget", "#2E7D32"
    over = cost - budget
    if over <= budget * 0.2:
        return f"⚠️ ${over:,}/yr over budget", "#E65100"
    return f"🚫 ${over:,}/yr over budget", "#B71C1C"


# ── Percentile-ranked batch scoring ───────────────────────────────────────────

def score_schools_df(user_profile: dict, df: pd.DataFrame) -> pd.DataFrame:
    """
    Score all schools using percentile ranking so scores spread across 0–10.

    Each dimension is ranked 0–1 relative to the other schools in df
    (not an absolute scale), so the best school always approaches 10
    and the worst approaches 0.

    Expects optional columns already on df:
      - field_earnings: field-specific median earnings (overrides earnings_10yr
        for the employment dimension when present)
      - has_target_field: True/False/None — adds a penalty for False schools
    """
    if df.empty:
        return df

    df = df.copy()
    is_intl = user_profile.get("nationality", "United States") != "United States"
    weights = user_profile.get("priority_weights") or {
        "cp_value": 3, "prestige": 2, "low_cost": 3, "employment": 2,
    }
    total_w = sum(weights.values()) or 1

    # ── Dimension 1: CP Value (higher value_score = better) ──────────────────
    df["_cp"] = df["value_score"].fillna(0).rank(pct=True, method="average")

    # ── Dimension 2: Prestige (lower admission rate = higher prestige) ────────
    df["_prestige"] = (1.0 - df["admission_rate"].fillna(0.5)).rank(
        pct=True, method="average"
    )

    # ── Dimension 3: Cost (lower cost = better) ───────────────────────────────
    if is_intl:
        cost_col = df["tuition_out"].fillna(df["net_price"]).fillna(55000)
    else:
        cost_col = df["net_price"].fillna(40000)
    # Negate: cheaper schools get a higher rank
    df["_cost"] = (-cost_col).rank(pct=True, method="average")

    # ── Dimension 4: Employment (higher earnings = better) ────────────────────
    # Use field_earnings where available, fall back to school-wide earnings
    if "field_earnings" in df.columns:
        earn_col = df["field_earnings"].fillna(df["earnings_10yr"]).fillna(0)
    else:
        earn_col = df["earnings_10yr"].fillna(0)
    df["_employ"] = earn_col.rank(pct=True, method="average")

    # ── Field presence penalty ────────────────────────────────────────────────
    # Schools confirmed to NOT have the user's field lose 0.15 from their raw score.
    if "has_target_field" in df.columns:
        df["_field_pen"] = df["has_target_field"].apply(
            lambda v: -0.15 if v is False else 0.0
        )
    else:
        df["_field_pen"] = 0.0

    # ── Weighted sum (0–1 scale, may go slightly negative after penalty) ──────
    df["_raw"] = (
        df["_cp"]      * weights.get("cp_value",  3) / total_w
        + df["_prestige"] * weights.get("prestige",  2) / total_w
        + df["_cost"]     * weights.get("low_cost",  3) / total_w
        + df["_employ"]   * weights.get("employment", 2) / total_w
        + df["_field_pen"]
    ).clip(0.0, 1.0)

    # ── Final percentile rank → 0–10 ─────────────────────────────────────────
    df["match_score"] = (
        df["_raw"].rank(pct=True, method="average") * 10
    ).round(1)

    # Drop temp columns
    df = df.drop(columns=[c for c in df.columns if c.startswith("_")])

    # ── Admission probability + budget fit (per-row) ──────────────────────────
    rows = df.to_dict("records")
    admit_probs, admit_cats, budget_texts, budget_colors = [], [], [], []
    for school in rows:
        prob, _ = estimate_admission_probability(user_profile, school)
        cat = classify_school(prob)
        bt, bc = get_budget_fit(user_profile, school)
        admit_probs.append(prob)
        admit_cats.append(cat)
        budget_texts.append(bt)
        budget_colors.append(bc)

    df["admit_prob"] = admit_probs
    df["admit_category"] = admit_cats
    df["budget_fit_text"] = budget_texts
    df["budget_fit_color"] = budget_colors

    return df
