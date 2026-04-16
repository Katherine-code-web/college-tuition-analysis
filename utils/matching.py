"""
Matching utilities for Smart School Matcher.

Admission probability estimates are rough approximations based on
publicly available score distributions only. They do NOT account for
essays, recommendations, demographics, yield management, or holistic review.
"""

import pandas as pd


# ── Admission Probability ──────────────────────────────────────────────────────

def estimate_admission_probability(
    user_profile: dict, school: dict
) -> tuple[float | None, bool]:
    """
    Estimate admission probability for a user at a given school.

    Returns (probability_0_to_1, has_score_data).
    has_score_data = True when test-score percentile data was used.
    """
    base_rate = school.get("admission_rate")
    if base_rate is None or base_rate <= 0:
        return None, False

    score_factor = 1.0
    has_score_data = False

    # SAT adjustment
    user_sat = user_profile.get("sat")
    sat_p25 = school.get("sat_p25")
    sat_p75 = school.get("sat_p75")

    if user_sat and sat_p25 and sat_p75:
        has_score_data = True
        mid = (sat_p25 + sat_p75) / 2
        if user_sat >= sat_p75:
            score_factor = 1.8   # above school's P75
        elif user_sat >= mid:
            score_factor = 1.3
        elif user_sat >= sat_p25:
            score_factor = 1.0
        else:
            score_factor = 0.5   # below school's P25
    else:
        # Fall back to ACT only when no SAT provided
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

    # GPA adjustment
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
    """Classify as Reach / Target / Safety based on estimated admit probability."""
    if prob is None:
        return "Unknown"
    if prob < 0.25:
        return "Reach"
    elif prob < 0.60:
        return "Target"
    else:
        return "Safety"


# ── Match Score ────────────────────────────────────────────────────────────────

def calculate_match_score(
    user_profile: dict, school: dict
) -> tuple[float, dict]:
    """
    Calculate personalized match score (0–10) from user's priority weights.

    Returns (total_score, component_scores_0_to_1).
    """
    weights = user_profile.get("priority_weights") or {
        "cp_value": 3, "prestige": 2, "low_cost": 3, "employment": 2
    }
    total_weight = sum(weights.values()) or 1
    norm = {k: v / total_weight for k, v in weights.items()}

    is_intl = user_profile.get("nationality", "United States") != "United States"
    scores = {}

    # 1) CP Value — value_score is already enriched by enrich_df
    vs = school.get("value_score")
    scores["cp_value"] = min(vs / 10.0, 1.0) if vs is not None else 0.3

    # 2) Prestige — use (1 - admit rate) as proxy
    adm = school.get("admission_rate")
    scores["prestige"] = (1.0 - adm) if adm is not None else 0.5

    # 3) Low cost relative to budget
    if is_intl:
        cost = school.get("tuition_out") or school.get("net_price") or 55000
    else:
        cost = school.get("net_price") or 40000
    budget = user_profile.get("annual_budget") or 50000
    if cost <= budget:
        scores["low_cost"] = 1.0 - (cost / budget) * 0.4  # cheapest=1.0, at-budget=0.6
    else:
        over_pct = (cost - budget) / budget
        scores["low_cost"] = max(0.0, 1.0 - over_pct * 1.5)

    # 4) Employment outcomes
    earn = school.get("earnings_10yr")
    scores["employment"] = min(earn / 120000, 1.0) if earn else 0.3

    total = sum(scores.get(k, 0) * norm.get(k, 0) for k in norm)
    return round(total * 10, 2), scores


# ── Budget Fit ─────────────────────────────────────────────────────────────────

def get_budget_fit(user_profile: dict, school: dict) -> tuple[str, str]:
    """Returns (display_text, color_hex) for budget fit indicator."""
    is_intl = user_profile.get("nationality", "United States") != "United States"
    cost = (school.get("tuition_out") if is_intl else None) or school.get("net_price")
    budget = user_profile.get("annual_budget") or 50000

    if cost is None:
        return "❓ Cost data unavailable", "#9E9E9E"
    if cost <= budget:
        return f"✓ Fits your ${budget:,} budget", "#2E7D32"
    over = cost - budget
    return f"⚠️ ${over:,}/yr over budget", "#E65100"


# ── Batch scoring ──────────────────────────────────────────────────────────────

def score_schools_df(user_profile: dict, df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply match score + admission probability to every row in the DataFrame.

    Adds columns:
      match_score, admit_prob, admit_category,
      budget_fit_text, budget_fit_color
    """
    df = df.copy()
    rows = df.to_dict("records")

    match_scores, admit_probs, admit_cats = [], [], []
    budget_texts, budget_colors = [], []

    for school in rows:
        ms, _ = calculate_match_score(user_profile, school)
        prob, _ = estimate_admission_probability(user_profile, school)
        cat = classify_school(prob)
        bt, bc = get_budget_fit(user_profile, school)

        match_scores.append(ms)
        admit_probs.append(prob)
        admit_cats.append(cat)
        budget_texts.append(bt)
        budget_colors.append(bc)

    df["match_score"] = match_scores
    df["admit_prob"] = admit_probs
    df["admit_category"] = admit_cats
    df["budget_fit_text"] = budget_texts
    df["budget_fit_color"] = budget_colors
    return df
