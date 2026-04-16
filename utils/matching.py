"""
Matching utilities for Smart School Matcher.

Admission probability estimates are rough approximations based on publicly
available score distributions only. They do NOT account for essays,
recommendations, demographics, yield management, or holistic review.
For graduate programs the base rate is further adjusted heuristically
because College Scorecard only provides institution-wide (undergrad) admit rates.
"""

import pandas as pd

_GRAD_DEGREES = {"Master's", "MBA", "Doctoral"}


# ── Grad admit rate adjustment ────────────────────────────────────────────────

def _estimate_grad_admit_rate(undergrad_rate: float, degree: str) -> float:
    """
    Heuristically adjust an undergrad admission rate to a graduate-level estimate.

    Graduate applicant pools are smaller and more self-selected, so most
    Master's / MBA programs admit a higher fraction of applicants than the
    corresponding undergrad program.  Doctoral programs are often more
    selective than undergrad.

    These are rough approximations — real program admit rates vary widely.
    """
    if degree == "Doctoral":
        # PhD programs tend to be more selective; keep close to undergrad rate
        # (some are higher, some lower — undergrad rate is weak signal either way)
        return min(undergrad_rate * 1.0, 0.40)

    # Master's / MBA
    if undergrad_rate < 0.10:
        # Very selective schools (e.g. MIT, Harvard): their MBA is also highly
        # selective, but admit rate is still higher than undergrad
        return min(undergrad_rate * 2.5, 0.45)
    elif undergrad_rate < 0.25:
        # Selective schools: MBA typically 30–50%
        return min(undergrad_rate * 2.2, 0.65)
    elif undergrad_rate < 0.50:
        # Moderately selective: grad programs usually more open
        return min(undergrad_rate * 1.8, 0.80)
    else:
        # Open-access / less selective: grad programs nearly as open
        return min(undergrad_rate * 1.3, 0.90)


# ── Admission Probability ──────────────────────────────────────────────────────

def estimate_admission_probability(
    user_profile: dict, school: dict
) -> tuple[float | None, bool]:
    """
    Estimate admission probability for a user at a given school.
    Returns (probability_0_to_1, has_score_data).

    For graduate programs (Master's / MBA / Doctoral) the institution-wide
    undergrad admit rate is adjusted via _estimate_grad_admit_rate before
    applying academic score factors.
    """
    base_rate = school.get("admission_rate")
    if base_rate is None or base_rate <= 0:
        return None, False

    # Adjust for graduate-level programs
    degree = user_profile.get("target_degree", "Bachelor's")
    if degree in _GRAD_DEGREES:
        base_rate = _estimate_grad_admit_rate(base_rate, degree)

    score_factor = 1.0
    has_score_data = False

    # SAT/ACT comparisons are only meaningful for undergrad applicants
    if degree not in _GRAD_DEGREES:
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

    # GPA factor applies to both undergrad and grad applicants
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
      - field_earnings:    field-specific median earnings (overrides earnings_10yr
                           for the employment dimension when present)
      - has_target_field:  True / None / False — False adds a penalty
      - reputation_bonus:  0.0–1.0 program reputation score from
                           utils.program_reputation (grad mode only)

    Grad mode (target_degree in Master's / MBA / Doctoral):
      The "CP Value" dimension is replaced by program reputation
      (reputation_bonus percentile rank) when that column is present and
      at least one school has a non-None score.  This corrects for the
      fact that value_score uses institution-wide undergrad earnings,
      which are misleading for graduate program comparisons.
    """
    if df.empty:
        return df

    df = df.copy()
    is_intl = user_profile.get("nationality", "United States") != "United States"
    weights = user_profile.get("priority_weights") or {
        "cp_value": 3, "prestige": 2, "low_cost": 3, "employment": 2,
    }
    total_w = sum(weights.values()) or 1

    target_degree = user_profile.get("target_degree", "Bachelor's")
    _is_grad = target_degree in _GRAD_DEGREES

    # ── Dimension 1: CP Value (undergrad) OR Program Reputation (grad) ────────
    use_reputation = (
        _is_grad
        and "reputation_bonus" in df.columns
        and df["reputation_bonus"].notna().any()
    )
    if use_reputation:
        # Fill None (unknown schools) with 0.5 so they land in the middle,
        # not at the bottom.  Schools in the lookup table compete on tier;
        # unknown schools are treated neutrally.
        df["_cp"] = df["reputation_bonus"].fillna(0.5).rank(pct=True, method="average")
    else:
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
