"""
Page 8 — Smart School Matcher
Personalized Reach / Target / Safety / Stretch school recommendations based on user profile.
"""

import streamlit as st
import pandas as pd
from utils.theme import get_theme_css
from utils.sidebar import render_profile_status
from utils.api import (
    fetch_candidate_schools, matcher_result_to_row,
    get_school_programs, fmt_usd, fmt_pct,
)
from utils.calculations import enrich_df, CIP_CATEGORIES
from utils.matching import score_schools_df, classify_school
from utils.field_suggestions import get_field_hint
from utils.program_reputation import get_reputation_score
from utils.earnings_fallback import get_field_earnings, get_program_salary, earnings_confidence_html, CONFIDENCE_BADGES

st.set_page_config(page_title="Smart Matcher", page_icon="🎯", layout="wide")
st.markdown(get_theme_css(), unsafe_allow_html=True)

lang = st.session_state.get("lang", "en")

# ── Guard: require profile ─────────────────────────────────────────────────────
profile = st.session_state.get("user_profile", {})
if not profile.get("profile_complete"):
    st.title("🎯 Smart School Matcher" if lang == "en" else "🎯 個人化學校配對")
    st.warning(
        "👉 Please fill out your profile first to get personalized recommendations!"
        if lang == "en"
        else "👉 請先填寫你的條件，才能獲得個人化推薦！"
    )
    if st.button(
        "📝 Go to My Profile" if lang == "en" else "📝 前往填寫條件",
        type="primary",
    ):
        st.switch_page("pages/7_My_Profile.py")
    st.stop()

# ── Sidebar: filter overrides ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔧 " + ("Adjust Filters" if lang == "en" else "調整篩選條件"))
    st.caption(
        "These override your profile for this search."
        if lang == "en"
        else "以下設定會覆蓋你的 profile 條件。"
    )

    budget_override = st.slider(
        "Annual Budget (USD)" if lang == "en" else "年預算（美元）",
        min_value=0, max_value=100000,
        value=int(profile.get("annual_budget", 50000)),
        step=5000,
        format="$%d",
        key="matcher_budget",
    )

    cip_keys = list(CIP_CATEGORIES.keys())
    cip_labels = list(CIP_CATEGORIES.values())
    default_cip = profile.get("target_field_cip", cip_keys[10])
    field_idx = cip_keys.index(default_cip) if default_cip in cip_keys else 10
    field_override = st.selectbox(
        "Field of Study" if lang == "en" else "目標科系",
        cip_labels,
        index=field_idx,
        key="matcher_field",
    )

    type_opts = ["Any", "Public", "Private Nonprofit"]
    type_override = st.selectbox(
        "School Type" if lang == "en" else "學校類型",
        type_opts,
        index=type_opts.index(profile.get("preferred_type", "Any"))
        if profile.get("preferred_type") in type_opts else 0,
        key="matcher_type",
    )

    include_no_data = st.toggle(
        "Include schools with missing data" if lang == "en" else "包含資料缺失學校",
        value=False,
        key="matcher_include_missing",
    )

    st.markdown("---")
    render_profile_status(lang)

# ── Title + Profile Recap ──────────────────────────────────────────────────────
st.title("🎯 Smart School Matcher" if lang == "en" else "🎯 個人化學校配對")

# Profile recap pill row
p = profile
gpa_str = f"GPA {p.get('gpa', 0):.1f}" if p.get("gpa") else ""
budget_str = f"${budget_override // 1000:.0f}k/yr"
deg_str = p.get("target_degree", "")
test_str = (
    f"{p.get('language_test','').split()[0]} {p.get('language_score','')}"
    if p.get("language_score") else ""
)
nat_str = p.get("nationality", "")
pills = [s for s in [nat_str, deg_str, gpa_str, test_str, budget_str] if s]

pill_html = "".join(
    f'<span style="background:#FFD166;border:2px solid #1A1A1A;border-radius:20px;'
    f'padding:4px 12px;margin:3px;font-size:0.83rem;font-weight:800;'
    f'display:inline-block;">{pill}</span>'
    for pill in pills
)
st.markdown(
    f'<div style="margin-bottom:8px;">{pill_html}</div>',
    unsafe_allow_html=True,
)

edit_col, _ = st.columns([1, 5])
with edit_col:
    if st.button("✏️ Edit Profile" if lang == "en" else "✏️ 修改條件"):
        st.switch_page("pages/7_My_Profile.py")

st.markdown(
    '> ⚠️ **Disclaimer:** Admission probability is a rough estimate based on '
    'publicly available score distributions only. It does NOT consider essays, '
    'recommendations, research, or institutional fit. Use as a starting point, '
    'not a final verdict.'
    if lang == "en"
    else
    '> ⚠️ **免責聲明：** 錄取機率僅根據公開的分數分布粗略估算，不考慮個人文件、推薦信、研究經歷或其他主觀因素，請僅作參考。'
)

st.markdown("---")

# ── Fetch & Score ──────────────────────────────────────────────────────────────
ownership_map = {"Any": 0, "Public": 1, "Private Nonprofit": 2}
ownership_code = ownership_map.get(type_override, 0)
preferred_states = tuple(profile.get("preferred_states", []))

if st.button(
    "🔍 Find My Matches" if lang == "en" else "🔍 開始配對",
    type="primary",
    use_container_width=False,
):
    st.session_state["matcher_run"] = True

if not st.session_state.get("matcher_run"):
    st.info(
        "👆 Click **Find My Matches** to load your personalized school list."
        if lang == "en"
        else "👆 點擊 **開始配對** 載入個人化學校清單。"
    )
    st.stop()

_GRAD_DEGREES = {"Master's", "MBA", "Doctoral"}

# Build an effective profile with sidebar overrides
effective_profile = {**profile, "annual_budget": budget_override}

# Derive CIP 2-digit prefix and degree from profile
target_degree_val = effective_profile.get("target_degree", "Bachelor's")
target_cip = effective_profile.get("target_field_cip", "")
cip_prefix = target_cip[:2] if target_cip else ""

_is_grad_mode = target_degree_val in _GRAD_DEGREES

# API-level degree filter: only HIGHDEG is used in the API call because
# the Scorecard API does not reliably support __range on PREDDEG/ICLEVEL.
# PREDDEG and ICLEVEL filtering is applied client-side after fetching.
_highest_degree = 4 if _is_grad_mode else (3 if target_degree_val == "Bachelor's" else 0)

with st.spinner(
    f"🔍 Searching schools offering {field_override}..." if lang == "en"
    else f"🔍 搜尋提供「{field_override}」的學校..."
):
    raw = fetch_candidate_schools(
        states=preferred_states,
        ownership=ownership_code,
        cip_2digit=cip_prefix,
        per_page=100,
        n_pages=2,
        highest_degree=_highest_degree,
    )
    # Fallback 1: drop state filter if too few results
    if len(raw) < 10 and preferred_states:
        raw = fetch_candidate_schools(
            states=(),
            ownership=ownership_code,
            cip_2digit=cip_prefix,
            per_page=100,
            n_pages=2,
            highest_degree=_highest_degree,
        )
    # Fallback 2: drop CIP filter too (API may not support it for all fields)
    if len(raw) < 10:
        raw = fetch_candidate_schools(
            states=preferred_states or (),
            ownership=ownership_code,
            cip_2digit="",
            per_page=100,
            n_pages=2,
            highest_degree=_highest_degree,
        )

rows = [matcher_result_to_row(r) for r in raw]
df = pd.DataFrame(rows)

if df.empty:
    st.error(
        "No schools found. Try adjusting your filters."
        if lang == "en"
        else "找不到符合條件的學校，請調整篩選條件。"
    )
    st.stop()

df = enrich_df(df)

# ── Client-side degree-level filter (PREDDEG / ICLEVEL) ──────────────────────
# The Scorecard API only reliably filters on HIGHDEG (highest_degree above).
# We apply PREDDEG and ICLEVEL here after fetching to further exclude
# vocational/community-college results for grad and bachelor's searches.
if _is_grad_mode:
    # PREDDEG >= 3: drop schools where most students get certificates/associates
    if "degree_pred" in df.columns:
        df = df[df["degree_pred"].isna() | (df["degree_pred"] >= 3)].copy()
    # ICLEVEL == 1: keep only 4-year institutions (or missing data)
    if "iclevel" in df.columns:
        df = df[df["iclevel"].isna() | (df["iclevel"] == 1)].copy()
elif target_degree_val == "Bachelor's":
    if "degree_pred" in df.columns:
        df = df[df["degree_pred"].isna() | (df["degree_pred"] >= 3)].copy()

# ── Budget hard cap: exclude schools > budget × 1.2 ──────────────────────────
_budget = budget_override or 50000
_is_intl = effective_profile.get("nationality", "United States") != "United States"

# COA resolution priority per spec:
# 1. International + public → tuition_out (COSTT4_OOS proxy)
# 2. International + private → tuition_out or net_price (COSTT4_A proxy)
# 3. Residency unknown → default to international logic
# 4. Missing COA → fall back to tuition_out + 18000 or net_price
def _resolve_coa(row: "pd.Series", is_intl: bool) -> "float | None":
    """Resolve Cost of Attendance from available fields."""
    if is_intl:
        coa = row.get("tuition_out")
        if pd.notna(coa) and coa:
            return float(coa)
        # Fall back to net_price (includes living costs at some schools)
        np_ = row.get("net_price")
        if pd.notna(np_) and np_:
            return float(np_)
        return None
    else:
        np_ = row.get("net_price")
        if pd.notna(np_) and np_:
            return float(np_)
        return None

df["effective_price"] = df.apply(lambda r: _resolve_coa(r, _is_intl), axis=1)

# Capture schools ABOVE budget × 1.2 before dropping them (for Stretch tab + banner)
_over_budget_mask = df["effective_price"].notna() & (df["effective_price"] > _budget * 1.2)
_over_budget_df = df[_over_budget_mask].copy()

# Keep schools that either have no price data OR are within 1.2× budget
_within_budget = df["effective_price"].isna() | (df["effective_price"] <= _budget * 1.2)
df = df[_within_budget].copy()

if not include_no_data:
    df = df.dropna(subset=["earnings_10yr", "net_price"])

if df.empty:
    if _is_grad_mode and _budget < 60000:
        st.error(
            f"No **{target_degree_val}** programs found within your **${_budget:,}/yr** budget. "
            "Most graduate programs cost $30k–$70k/yr in tuition. "
            "Try increasing your annual budget in the sidebar (suggested: $50,000–$70,000)."
            if lang == "en"
            else f"在 **${_budget:,}/yr** 預算內找不到 **{target_degree_val}** 課程。"
                 "大多數研究所課程每年學費為 $30k–$70k。建議在左側將年預算提高至 $50,000–$70,000。"
        )
    else:
        st.error(
            "No schools match your budget and data requirements. "
            "Try increasing your annual budget in the sidebar or toggle "
            "'Include schools with missing data'."
            if lang == "en"
            else "找不到符合預算且有完整資料的學校。請在左側提高年預算，或開啟「包含資料缺失學校」。"
        )
    st.stop()

# Warn (but don't stop) when very few schools pass all filters
if len(df) < 10 and _is_grad_mode:
    st.warning(
        f"Only **{len(df)} schools** found after applying budget and degree-level filters. "
        "Consider raising your annual budget or removing state/type filters to see more options."
        if lang == "en"
        else f"套用預算與學位層級篩選後，僅找到 **{len(df)} 所學校**。"
             "建議提高年預算或移除州別/類型篩選，以查看更多選項。"
    )

# ── Fetch field-specific earnings BEFORE scoring ──────────────────────────────
# This lets score_schools_df use field_earnings in the employment dimension
# so the percentile ranking reflects your actual target field.
# Also tracks field_size (number of CIP sub-programs) as a program scale proxy.
field_earn_map: dict[int, float] = {}
field_present_map: dict[int, bool | None] = {}
field_size_map: dict[int, int] = {}

if cip_prefix:
    with st.spinner(
        f"🎓 Checking {field_override} program data..."
        if lang == "en"
        else f"🎓 查詢「{field_override}」科系薪資資料..."
    ):
        candidate_ids = df["id"].dropna().astype(int).tolist()[:50]
        for school_id in candidate_ids:
            try:
                programs = get_school_programs(school_id)
                # All programs in this CIP category (regardless of earnings)
                cip_programs = [
                    p for p in programs
                    if str(p.get("cip_code", ""))[:2] == cip_prefix
                ]
                # Track program breadth (number of sub-programs) as proxy for dept size
                field_size_map[school_id] = len(cip_programs)
                # Subset that also have earnings data
                with_earnings = [p for p in cip_programs if p.get("median_earnings")]
                if with_earnings:
                    # School offers field AND has earnings data
                    field_earn_map[school_id] = max(p["median_earnings"] for p in with_earnings)
                    field_present_map[school_id] = True
                elif cip_programs:
                    # School offers field but earnings are suppressed (e.g. Harvard MBA)
                    # Use None so it gets no penalty — it does have the program
                    field_present_map[school_id] = None
                else:
                    # School genuinely doesn't offer this field
                    field_present_map[school_id] = False
            except Exception:
                pass

    df["field_earnings"] = df["id"].apply(
        lambda x: field_earn_map.get(int(x)) if pd.notna(x) else None
    )
    df["has_target_field"] = df["id"].apply(
        lambda x: field_present_map.get(int(x)) if pd.notna(x) else None
    )
    df["field_size"] = df["id"].apply(
        lambda x: field_size_map.get(int(x), 0) if pd.notna(x) else 0
    )

# ── Layer 2/3 earnings fallback ───────────────────────────────────────────────
# When College Scorecard program earnings are suppressed, look up national
# estimates from ACS PUMS (Layer 2) or BLS OEWS (Layer 3).
# Attach both a fallback_earnings column (used for scoring) and
# earnings_confidence column (used for UI badge display).
_national_fallback: dict = {}
if cip_prefix:
    _national_fallback = get_field_earnings(cip_prefix, target_degree_val)

def _resolve_earnings(row: pd.Series) -> tuple[float | None, str]:
    """
    Return (earnings_value, confidence_level) for one school row.

    4-layer priority:
      1. College Scorecard program-level earnings (school + field specific)
      2. program_starting_salary.csv (school + program specific, our curated data)
      3. National ACS/BLS field-level median (same for all schools — used only if
         no school-specific data exists)
      4. School-wide 10-year earnings from Scorecard (last resort)
    """
    # Layer 1: Scorecard program-level earnings
    prog_earn = row.get("field_earnings")
    if pd.notna(prog_earn) and prog_earn:
        return prog_earn, "program"

    # Layer 2: school-specific program salary from our curated CSV
    if cip_prefix:
        school_sal = get_program_salary(
            school_name=row.get("name", ""),
            unitid=row.get("id"),
            cip_2digit=cip_prefix,
            credential_level=target_degree_val,
        )
        if school_sal:
            return school_sal, "program"

    # Layer 3: national ACS/BLS field-level median (same value for all schools)
    nat_median = _national_fallback.get("median")
    if nat_median:
        return nat_median, _national_fallback.get("confidence", "field_national")

    # Layer 4: school-wide 10-year earnings
    inst_earn = row.get("earnings_10yr")
    if pd.notna(inst_earn) and inst_earn:
        return inst_earn, "institution"

    return None, "institution"

_earn_vals, _earn_confs = zip(*[_resolve_earnings(row) for _, row in df.iterrows()]) if not df.empty else ([], [])
df["display_earnings"] = list(_earn_vals)
df["earnings_confidence"] = list(_earn_confs)

# ── Reputation bonus (grad mode) ──────────────────────────────────────────────
# For graduate programs, add program reputation scores from the lookup table.
# score_schools_df uses this column to replace the cp_value dimension
# (which is based on institution-wide undergrad earnings — misleading for grad).
if cip_prefix and target_degree_val in _GRAD_DEGREES:
    all_ids = df["id"].dropna().astype(int).tolist()
    df["reputation_bonus"] = df["id"].apply(
        lambda x: get_reputation_score(cip_prefix, target_degree_val, int(x))
        if pd.notna(x) else None
    )

# Pass display_earnings into field_earnings so score_schools_df uses the best
# available signal (program-specific CSV > national ACS > institution) for the
# employment dimension.  Override where Scorecard program earnings are missing
# but a better fallback was found (either from our CSV or from ACS/BLS).
if "field_earnings" in df.columns and "display_earnings" in df.columns:
    use_fallback = df["earnings_confidence"].isin(["program", "field_national", "occupation"])
    df["field_earnings"] = df["field_earnings"].fillna(
        df["display_earnings"].where(use_fallback)
    )

df = score_schools_df(effective_profile, df)
df = df.sort_values("match_score", ascending=False).reset_index(drop=True)

# ── Score over-budget schools for Stretch tab ─────────────────────────────────
# Apply same field earnings / reputation to the over-budget df before scoring
if not _over_budget_df.empty:
    if cip_prefix and "field_earnings" in df.columns:
        _over_budget_df["field_earnings"] = _over_budget_df["id"].apply(
            lambda x: field_earn_map.get(int(x)) if pd.notna(x) else None
        )
        _over_budget_df["has_target_field"] = _over_budget_df["id"].apply(
            lambda x: field_present_map.get(int(x)) if pd.notna(x) else None
        )
        _over_budget_df["field_size"] = _over_budget_df["id"].apply(
            lambda x: field_size_map.get(int(x), 0) if pd.notna(x) else 0
        )
        # Apply fallback earnings to over-budget df
        _ob_earn_vals, _ob_earn_confs = zip(*[_resolve_earnings(row) for _, row in _over_budget_df.iterrows()]) if not _over_budget_df.empty else ([], [])
        _over_budget_df["display_earnings"] = list(_ob_earn_vals)
        _over_budget_df["earnings_confidence"] = list(_ob_earn_confs)
        use_fallback_ob = _over_budget_df["earnings_confidence"].isin(["program", "field_national", "occupation"])
        _over_budget_df["field_earnings"] = _over_budget_df["field_earnings"].fillna(
            _over_budget_df["display_earnings"].where(use_fallback_ob)
        )
    if cip_prefix and target_degree_val in _GRAD_DEGREES and "reputation_bonus" in df.columns:
        _over_budget_df["reputation_bonus"] = _over_budget_df["id"].apply(
            lambda x: get_reputation_score(cip_prefix, target_degree_val, int(x))
            if pd.notna(x) else None
        )
    _over_budget_df = enrich_df(_over_budget_df)
    _over_budget_df = score_schools_df(effective_profile, _over_budget_df)
    _over_budget_df = _over_budget_df.sort_values("match_score", ascending=False).reset_index(drop=True)

# ── Build Stretch candidates ───────────────────────────────────────────────────
# Stretch: excluded by budget, but COA <= budget × 1.8
# Note: SCH_AVG_INST_AID / PCT_INST_AID not in current data pipeline;
# use pell_rate as proxy for pct_receiving_aid.
# avg_institutional_aid is not available — see CHANGES.md.
# Stretch filter uses only fields available: match_score >= 7.0 + COA range.
_stretch_df = pd.DataFrame()
_n_suppressed_aid = 0
if not _over_budget_df.empty:
    _ob = _over_budget_df.copy()
    # COA <= budget × 1.8
    _ob_feasible = _ob[_ob["effective_price"] <= _budget * 1.8].copy()
    # match_score >= 7.0
    if "match_score" in _ob_feasible.columns:
        _ob_feasible = _ob_feasible[_ob_feasible["match_score"] >= 7.0]
    # pell_rate >= 0.3 as proxy for pct_receiving_aid
    if "pell_rate" in _ob_feasible.columns:
        _ob_feasible = _ob_feasible[
            _ob_feasible["pell_rate"].isna() | (_ob_feasible["pell_rate"] >= 0.3)
        ]
    # Count suppressed aid (pell_rate null = aid data unavailable)
    _n_suppressed_aid = int(_ob_feasible["pell_rate"].isna().sum())
    # Sub-tiering
    def _stretch_tier(coa, budget):
        if coa <= budget * 1.3:
            return 1
        return 2
    if not _ob_feasible.empty:
        _ob_feasible["stretch_tier"] = _ob_feasible["effective_price"].apply(
            lambda c: _stretch_tier(c, _budget)
        )
        _ob_feasible["realistic_net_cost"] = _ob_feasible["effective_price"].apply(
            lambda c: c  # no avg_inst_aid available; net cost = sticker price
        )
        _ob_feasible["budget_gap"] = _ob_feasible["effective_price"] - _budget
        # Sort: tier first, then match_score descending
        _stretch_df = _ob_feasible.sort_values(
            ["stretch_tier", "match_score"], ascending=[True, False]
        ).reset_index(drop=True)

# ── Log excluded schools to session state ─────────────────────────────────────
st.session_state["excluded_by_budget"] = (
    _over_budget_df[["id", "name", "effective_price", "match_score"]].to_dict("records")
    if not _over_budget_df.empty else []
)

# Split into categories
reach_df = df[df["admit_category"] == "Reach"].head(5)
target_df = df[df["admit_category"] == "Target"].head(5)
safety_df = df[df["admit_category"] == "Safety"].head(5)
unknown_df = df[df["admit_category"] == "Unknown"].head(3)

# ── Excluded-schools banner ────────────────────────────────────────────────────
_n_excluded = len(_over_budget_df) if not _over_budget_df.empty else 0
if _n_excluded > 0:
    # Top 3 excluded by match score
    _top_excluded_names = (
        _over_budget_df.nlargest(3, "match_score")["name"].tolist()
        if "match_score" in _over_budget_df.columns
        else _over_budget_df.head(3)["name"].tolist()
    )
    _top_names_str = ", ".join(_top_excluded_names) if _top_excluded_names else "N/A"
    _stretch_count = len(_stretch_df) if not _stretch_df.empty else 0
    st.warning(
        f"**{_n_excluded} school{'s' if _n_excluded != 1 else ''} excluded** by your "
        f"**${_budget:,}/yr** budget — including {_top_names_str}. "
        + (f"See the **Stretch** tab below for {_stretch_count} school{'s' if _stretch_count != 1 else ''} where scholarships may close the gap."
           if _stretch_count > 0
           else "None qualify for the Stretch tab (aid data suppressed or cost too high).")
        if lang == "en"
        else
        f"**{_n_excluded} 所學校** 因超出你的 **${_budget:,}/yr** 預算而被排除 — 包含 {_top_names_str}。"
        + (f"請查看下方 **Stretch** 標籤，了解 {_stretch_count} 所可能透過獎學金彌補差距的學校。"
           if _stretch_count > 0
           else "無符合 Stretch 標籤條件的學校（助學金資料被隱藏或費用過高）。")
    )

field_label = field_override if lang == "en" else field_override
if "has_target_field" in df.columns:
    n_with_field = int(
        (df["has_target_field"] == True).sum()  # noqa: E712
        + df["has_target_field"].isna().sum()
    )
    n_with_earnings = int((df["has_target_field"] == True).sum())  # noqa: E712
    n_suppressed = int(df["has_target_field"].isna().sum())
else:
    n_with_field = n_with_earnings = len(df)
    n_suppressed = 0

# ── Summary line ──────────────────────────────────────────────────────────────
if n_suppressed > 0 and n_with_earnings == 0:
    # All earnings suppressed — prominent warning for grad users
    st.markdown(
        f"**{len(df)} schools scored** — {n_with_field} offer **{field_label}** programs "
        f"(earnings data suppressed for all {n_suppressed})."
        if lang == "en"
        else f"**已評分 {len(df)} 所學校** — {n_with_field} 所提供「{field_label}」科系"
             f"（全部 {n_suppressed} 所的薪資資料均被隱藏）。"
    )
    if _is_grad_mode:
        st.warning(
            f"⚠️ **Data limitation:** All {n_with_field} schools offering "
            f"**{field_label}** at {target_degree_val} level have their program earnings "
            "suppressed by the U.S. Dept. of Education (privacy protection for small cohorts).\n\n"
            "**What this means:**\n"
            "- Earnings shown below are **institution-wide averages**, not specific to your field\n"
            "- Schools strong in engineering/CS may appear inflated\n"
            "- **Match scores in grad mode use program reputation as the primary quality signal** "
            "(based on commonly cited rankings)\n\n"
            "**Recommended next step:** Verify each school's program reputation using "
            "U.S. News, Bloomberg Businessweek, or Poets & Quants."
            if lang == "en"
            else
            f"⚠️ **資料限制：** 所有 {n_with_field} 所提供「{field_label}」{target_degree_val} "
            "課程的學校，其科系薪資資料均被美國教育部以隱私保護為由而隱藏。\n\n"
            "**這代表：**\n"
            "- 下方顯示的薪資為**學校整體平均**，非你科系的特定數據\n"
            "- 工程/CS 強校的整體薪資會被高估\n"
            "- **研究所模式下，配對分數以課程聲望作為主要品質指標**（依常見排名）\n\n"
            "**建議下一步：** 用 U.S. News、彭博商業周刊或 Poets & Quants 驗證各校課程聲望。"
        )
elif n_suppressed > 0:
    st.markdown(
        f"**{len(df)} schools scored** — {n_with_field} offer **{field_label}** programs "
        f"({n_with_earnings} have earnings data · {n_suppressed} suppressed)."
        if lang == "en"
        else f"**已評分 {len(df)} 所學校** — {n_with_field} 所提供「{field_label}」科系"
             f"（{n_with_earnings} 所有薪資資料 · {n_suppressed} 所被隱藏）。"
    )
else:
    st.markdown(
        f"**{len(df)} schools scored** — {n_with_field} offer **{field_label}** programs."
        if lang == "en"
        else f"**已評分 {len(df)} 所學校** — {n_with_field} 所提供「{field_label}」科系。"
    )

# ── "Field earnings suppressed" explainer expander ─────────────────────────────
if n_suppressed > 0:
    with st.expander(
        "📊 Why do some schools show 'Field earnings suppressed'?"
        if lang == "en"
        else "📊 為什麼某些學校顯示「科系薪資被隱藏」？"
    ):
        st.markdown(
            """
**"Field earnings suppressed"** means the U.S. Department of Education has withheld
program-level earnings data for that school and field combination.

**Why does this happen?**
The Department suppresses earnings data when a cohort has **fewer than 30 graduates**
in a reporting period — this is a **federal privacy protection** to prevent
identifying individual students from small groups.

**What does it mean for you?**
- The school *does* offer your target field/program
- There just aren't enough recent graduates for the government to publish a median salary
- This is common at elite programs (e.g. Harvard MBA, Stanford GSB) where cohort
  reporting categories can be narrow
- It does **not** mean the program has poor earnings — often the opposite

**What we do instead:**
- Match scores in grad mode use **program reputation** as the primary quality signal
- Earnings shown are institution-wide medians (a fallback, labeled accordingly)
- You can find program-specific salary data at: U.S. News, Bloomberg Businessweek,
  Poets & Quants, or each school's employment report
            """
            if lang == "en"
            else
            """
**「科系薪資被隱藏」** 代表美國教育部已隱藏該校在特定科系的課程薪資資料。

**為什麼會發生？**
教育部會隱藏特定期間內**畢業生人數少於 30 人**的課程薪資資料 — 這是**聯邦隱私保護**措施，
防止從小群體中識別出個別學生。

**對你代表什麼？**
- 該校*確實*提供你的目標科系/課程
- 只是近期畢業生不足，政府無法公布薪資中位數
- 這在頂尖課程（如哈佛 MBA、史丹佛 GSB）很常見
- 這**不**代表該課程薪資差，往往恰恰相反

**我們的替代方案：**
- 研究所模式下，配對分數以**課程聲望**為主要品質指標
- 顯示的薪資為學校整體中位數（備援資料，有標示說明）
- 你可以在以下資源查詢課程特定薪資：U.S. News、彭博商業周刊、Poets & Quants 或各校就業報告
            """
        )

# Credential hint — only when no school offers the field at all (not just suppressed)
if cip_prefix and "has_target_field" in df.columns and n_with_field == 0 and n_suppressed == 0:
    hint = get_field_hint(cip_prefix, lang)
    if hint:
        st.warning(hint)
    else:
        st.warning(
            f"⚠️ No schools in results offer **{field_label}** programs. "
            "Schools below are ranked by overall fit instead."
            if lang == "en"
            else f"⚠️ 結果中沒有學校提供「{field_label}」科系，以整體條件排名取代。"
        )

# ── School Card Helper ─────────────────────────────────────────────────────────

def school_card(row: dict, category_label: str, category_color: str) -> str:
    """Return HTML for a single school card."""
    name = row.get("name", "Unknown")
    location = f"{row.get('city', '')}, {row.get('state', '')}"
    school_type = row.get("type_en", "")
    match_score = row.get("match_score", 0)
    admit_prob = row.get("admit_prob")
    _is_grad_card = target_degree_val in _GRAD_DEGREES
    if admit_prob is not None:
        prob_str = f"{admit_prob * 100:.0f}% admit chance"
        if _is_grad_card:
            prob_str += " <span style='font-size:0.7rem;color:#aaa;'>est.</span>"
    else:
        prob_str = "N/A"

    is_intl = effective_profile.get("nationality", "United States") != "United States"
    cost = (row.get("tuition_out") if is_intl else None) or row.get("net_price")
    cost_str = fmt_usd(cost) if cost else "N/A"
    cost_label = (
        ("Out-of-state tuition" if is_intl else "Net price (after aid)")
        if lang == "en"
        else ("外州學費" if is_intl else "淨學費（助學金後）")
    )

    has_field = row.get("has_target_field")
    earn_val = row.get("display_earnings") or row.get("field_earnings") or row.get("earnings_10yr")
    earn_conf = row.get("earnings_confidence", "institution")
    earn_str = fmt_usd(earn_val) if earn_val else "N/A"
    earn_badge = earnings_confidence_html(earn_conf, lang) if earn_str != "N/A" else ""
    grad_str = fmt_pct(row.get("completion_rate"))
    budget_text = row.get("budget_fit_text", "")
    budget_color = row.get("budget_fit_color", "#555")

    field_tag = ""
    if has_field is True:
        field_tag = (
            '<span style="background:#DDFAE4;border:1.5px solid #6BCB77;border-radius:20px;'
            'padding:3px 10px;font-size:0.75rem;font-weight:800;">✓ Offers your field</span>'
        )
    elif has_field is None and cip_prefix:
        # School has the program but earnings are suppressed (e.g. elite MBA programs)
        field_tag = (
            '<span style="background:#EEF2FF;border:1.5px solid #7B8CE4;border-radius:20px;'
            'padding:3px 10px;font-size:0.75rem;font-weight:800;">📊 Field earnings suppressed</span>'
        )
    elif has_field is False:
        field_tag = (
            '<span style="background:#FFF3E8;border:1.5px solid #FF8C42;border-radius:20px;'
            'padding:3px 10px;font-size:0.75rem;font-weight:800;">⚠️ Field not offered</span>'
        )

    filled = round(match_score / 2)
    stars = "★" * filled + "☆" * (5 - filled)

    url = row.get("url", "")
    url_btn = (
        f'<a href="http://{url}" target="_blank" style="'
        f'display:inline-block;background:#4D96FF;color:white;border:2px solid #1A1A1A;'
        f'border-radius:8px;padding:6px 14px;font-size:0.82rem;font-weight:800;'
        f'text-decoration:none;font-family:Fredoka One,cursive;">'
        f'{"🔗 View School" if lang == "en" else "🔗 查看學校"}</a>'
        if url else ""
    )

    return f"""
<div style="
    background: white;
    border: 2.5px solid #1A1A1A;
    border-radius: 16px;
    box-shadow: 4px 4px 0px #1A1A1A;
    padding: 20px 22px;
    margin-bottom: 16px;
">
  <!-- Category badge -->
  <div style="margin-bottom: 10px;">
    <span style="background:{category_color};color:white;font-size:0.72rem;font-weight:800;
        letter-spacing:1.5px;border:2px solid #1A1A1A;border-radius:6px;
        padding:3px 10px;">{category_label}</span>
  </div>

  <!-- School name + location -->
  <div style="font-family:'Fredoka One',cursive;font-size:1.15rem;
      color:#1A1A1A;line-height:1.3;margin-bottom:4px;
      word-break:break-word;overflow-wrap:anywhere;">{name}</div>
  <div style="font-size:0.83rem;color:#777;margin-bottom:14px;
      word-break:break-word;overflow-wrap:anywhere;">
    📍 {location} &nbsp;·&nbsp; {school_type}
  </div>

  <!-- Match score + admit prob -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
    <div style="background:#FFF8F0;border:1.5px solid #FFD166;border-radius:10px;padding:10px 12px;min-width:0;overflow:hidden;">
      <div style="font-size:0.72rem;color:#888;margin-bottom:2px;">
        {'Match Score' if lang == 'en' else '配對分數'}
      </div>
      <div style="font-family:'Fredoka One',cursive;font-size:1.3rem;color:#FF8C42;line-height:1;">
        {match_score} <span style="font-size:0.85rem;">/10</span>
      </div>
      <div style="font-size:0.82rem;color:#FFB347;">{stars}</div>
    </div>
    <div style="background:#F8F8FF;border:1.5px solid #C5C5F0;border-radius:10px;padding:10px 12px;min-width:0;overflow:hidden;">
      <div style="font-size:0.72rem;color:#888;margin-bottom:2px;">
        {'Est. Admit' if lang == 'en' else '估算錄取率'}
      </div>
      <div style="font-family:'Fredoka One',cursive;font-size:1.1rem;color:#1A1A1A;line-height:1.2;word-break:break-word;">
        {prob_str}
      </div>
    </div>
  </div>

  <!-- Key metrics -->
  <div style="border-top:1.5px dashed #E0E0E0;padding-top:12px;margin-bottom:12px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
      <div style="min-width:0;overflow:hidden;">
        <div style="font-size:0.72rem;color:#888;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          💰 {cost_label}
        </div>
        <div style="font-size:0.92rem;font-weight:800;color:#1A1A1A;word-break:break-word;">{cost_str}</div>
      </div>
      <div style="min-width:0;overflow:hidden;">
        <div style="font-size:0.72rem;color:#888;">
          💼 {'Earnings' if lang == 'en' else '薪資'}
        </div>
        <div style="font-size:0.92rem;font-weight:800;color:#1A1A1A;">{earn_str}</div>
        {f'<div style="margin-top:3px;">{earn_badge}</div>' if earn_badge else ''}
      </div>
      <div style="min-width:0;overflow:hidden;">
        <div style="font-size:0.72rem;color:#888;">
          🎓 {'Grad Rate' if lang == 'en' else '畢業率'}
        </div>
        <div style="font-size:0.92rem;font-weight:800;color:#1A1A1A;">{grad_str}</div>
      </div>
      <div style="min-width:0;overflow:hidden;">
        <div style="font-size:0.72rem;color:#888;">
          📊 {'Budget fit' if lang == 'en' else '預算符合度'}
        </div>
        <div style="font-size:0.82rem;font-weight:800;color:{budget_color};word-break:break-word;">{budget_text}</div>
      </div>
    </div>
  </div>

  <!-- Field tag + link -->
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div>{field_tag}</div>
    <div>{url_btn}</div>
  </div>
</div>
"""


def render_cards_2col(category_df, label, color, empty_msg):
    """Render school cards in a 2-column grid within a tab."""
    if category_df.empty:
        st.info(empty_msg)
        return
    rows_list = [row.to_dict() for _, row in category_df.iterrows()]
    # Pair up cards into rows of 2
    for i in range(0, len(rows_list), 2):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(school_card(rows_list[i], label, color), unsafe_allow_html=True)
        with c2:
            if i + 1 < len(rows_list):
                st.markdown(school_card(rows_list[i + 1], label, color), unsafe_allow_html=True)


# ── Stretch card helper ────────────────────────────────────────────────────────
def stretch_card(row: dict) -> str:
    """Return HTML for a single Stretch school card."""
    name = row.get("name", "Unknown")
    location = f"{row.get('city', '')}, {row.get('state', '')}"
    school_type = row.get("type_en", "")
    match_score = row.get("match_score", 0)
    coa = row.get("effective_price", 0) or 0
    budget_gap = row.get("budget_gap", 0) or 0
    tier = row.get("stretch_tier", 2)
    pell = row.get("pell_rate")

    if tier == 1:
        tier_label = "NEGOTIABLE GAP"
        tier_color = "#6BCB77"
        tier_bg = "#DDFAE4"
        tier_border = "#6BCB77"
    else:
        tier_label = "AGGRESSIVE STRETCH"
        tier_color = "#F4A261"
        tier_bg = "#FFF8E8"
        tier_border = "#F4A261"

    coa_str = fmt_usd(coa)
    gap_str = fmt_usd(budget_gap)
    pell_str = f"{pell * 100:.0f}%" if pell is not None else "N/A"

    # Aid note: avg_institutional_aid not in pipeline
    aid_note = (
        "<span style='font-size:0.75rem;color:#888;'>"
        "Avg. institutional aid: <em>data unavailable</em> — see CHANGES.md</span>"
    )

    filled = round(match_score / 2)
    stars = "★" * filled + "☆" * (5 - filled)

    url = row.get("url", "")
    url_btn = (
        f'<a href="http://{url}" target="_blank" style="'
        f'display:inline-block;background:#4D96FF;color:white;border:2px solid #1A1A1A;'
        f'border-radius:8px;padding:6px 14px;font-size:0.82rem;font-weight:800;'
        f'text-decoration:none;font-family:Fredoka One,cursive;">'
        f'{"🔗 View School" if lang == "en" else "🔗 查看學校"}</a>'
        if url else ""
    )

    return f"""
<div style="
    background: white;
    border: 2.5px solid #1A1A1A;
    border-radius: 16px;
    box-shadow: 4px 4px 0px #1A1A1A;
    padding: 20px 22px;
    margin-bottom: 16px;
">
  <!-- Tier badge -->
  <div style="margin-bottom: 10px;display:flex;gap:8px;flex-wrap:wrap;">
    <span style="background:{tier_color};color:white;font-size:0.72rem;font-weight:800;
        letter-spacing:1.5px;border:2px solid #1A1A1A;border-radius:6px;
        padding:3px 10px;">💰 STRETCH</span>
    <span style="background:{tier_bg};color:{tier_color};font-size:0.72rem;font-weight:800;
        letter-spacing:1px;border:2px solid {tier_border};border-radius:6px;
        padding:3px 10px;">{tier_label}</span>
  </div>

  <!-- School name + location -->
  <div style="font-family:'Fredoka One',cursive;font-size:1.15rem;
      color:#1A1A1A;line-height:1.3;margin-bottom:4px;
      word-break:break-word;overflow-wrap:anywhere;">{name}</div>
  <div style="font-size:0.83rem;color:#777;margin-bottom:14px;
      word-break:break-word;overflow-wrap:anywhere;">
    📍 {location} &nbsp;·&nbsp; {school_type}
  </div>

  <!-- Match score -->
  <div style="background:#FFF8F0;border:1.5px solid #FFD166;border-radius:10px;
      padding:10px 12px;margin-bottom:14px;display:inline-block;">
    <div style="font-size:0.72rem;color:#888;margin-bottom:2px;">
      {'Match Score' if lang == 'en' else '配對分數'}
    </div>
    <div style="font-family:'Fredoka One',cursive;font-size:1.3rem;color:#FF8C42;line-height:1;">
      {match_score} <span style="font-size:0.85rem;">/10</span>
    </div>
    <div style="font-size:0.82rem;color:#FFB347;">{stars}</div>
  </div>

  <!-- Financial breakdown -->
  <div style="border-top:1.5px dashed #E0E0E0;padding-top:12px;margin-bottom:12px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
      <div>
        <div style="font-size:0.72rem;color:#888;">💸 Sticker Price (COA)</div>
        <div style="font-size:0.92rem;font-weight:800;color:#B71C1C;">{coa_str}</div>
      </div>
      <div>
        <div style="font-size:0.72rem;color:#888;">🎓 % Receiving Aid (Pell proxy)</div>
        <div style="font-size:0.92rem;font-weight:800;color:#1A1A1A;">{pell_str}</div>
      </div>
      <div>
        <div style="font-size:0.72rem;color:#888;">⚠️ Need to Negotiate / Self-fund</div>
        <div style="font-size:0.92rem;font-weight:800;color:#E65100;">{gap_str}/yr</div>
      </div>
      <div>
        <div style="font-size:0.72rem;color:#888;">📊 Avg Institutional Aid</div>
        {aid_note}
      </div>
    </div>
  </div>

  <!-- CTA -->
  <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div>{url_btn}</div>
  </div>
</div>
"""


def render_stretch_cards_2col(stretch_df_arg):
    """Render stretch school cards in a 2-column grid."""
    rows_list = [row.to_dict() for _, row in stretch_df_arg.iterrows()]
    for i in range(0, len(rows_list), 2):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(stretch_card(rows_list[i]), unsafe_allow_html=True)
            # Plan Negotiation button
            school_data = rows_list[i]
            if st.button(
                f"💬 Plan Negotiation for {school_data.get('name','')[:30]}",
                key=f"stretch_neg_{i}",
            ):
                st.session_state["negotiator_prefill"] = {
                    "name": school_data.get("name", ""),
                    "cost": school_data.get("effective_price", 0),
                    "match_score": school_data.get("match_score", 0),
                }
                st.switch_page("pages/09_Scholarship_Negotiator.py")
        with c2:
            if i + 1 < len(rows_list):
                school_data2 = rows_list[i + 1]
                st.markdown(stretch_card(school_data2), unsafe_allow_html=True)
                if st.button(
                    f"💬 Plan Negotiation for {school_data2.get('name','')[:30]}",
                    key=f"stretch_neg_{i+1}",
                ):
                    st.session_state["negotiator_prefill"] = {
                        "name": school_data2.get("name", ""),
                        "cost": school_data2.get("effective_price", 0),
                        "match_score": school_data2.get("match_score", 0),
                    }
                    st.switch_page("pages/09_Scholarship_Negotiator.py")


# ── Tabs: Reach / Target / Safety / Stretch ───────────────────────────────────
st.markdown("---")

_stretch_count_tab = len(_stretch_df) if not _stretch_df.empty else 0
tab_reach, tab_target, tab_safety, tab_stretch = st.tabs([
    f"🎯 Reach  ({len(reach_df)})" if lang == "en" else f"🎯 挑戰型 ({len(reach_df)})",
    f"✓ Target  ({len(target_df)})" if lang == "en" else f"✓ 目標型 ({len(target_df)})",
    f"🛡️ Safety  ({len(safety_df)})" if lang == "en" else f"🛡️ 保底型 ({len(safety_df)})",
    f"💰 Stretch  ({_stretch_count_tab})" if lang == "en" else f"💰 拉伸型 ({_stretch_count_tab})",
])

with tab_reach:
    st.caption(
        "Low admit probability — stretch yourself. These schools are worth applying if your match score is strong."
        if lang == "en"
        else "錄取機率較低的挑戰型學校。如果配對分數高，仍值得申請。"
    )
    render_cards_2col(
        reach_df, "🎯 REACH", "#E8503A",
        "No reach schools found. Try removing state/type filters."
        if lang == "en" else "找不到挑戰型學校，試試移除州別/類型篩選。",
    )

with tab_target:
    st.caption(
        "Realistic admit chance with good overall fit — your primary application list."
        if lang == "en"
        else "錄取機率合理、整體條件相符的目標學校 — 主要申請名單。"
    )
    render_cards_2col(
        target_df, "✓ TARGET", "#FF8C42",
        "No target schools found. Try removing state/type filters."
        if lang == "en" else "找不到目標型學校，試試移除州別/類型篩選。",
    )

with tab_safety:
    st.caption(
        "High likelihood of admission — include at least 2–3 safety schools in your list."
        if lang == "en"
        else "錄取機率高的保底學校 — 建議申請清單中至少包含 2–3 所。"
    )
    render_cards_2col(
        safety_df, "🛡️ SAFETY", "#6BCB77",
        "No safety schools found. Try removing state/type filters."
        if lang == "en" else "找不到保底型學校，試試移除州別/類型篩選。",
    )

with tab_stretch:
    st.caption(
        "Schools above your budget that may be bridgeable with institutional aid. "
        "**Stretch is independent of Reach/Target/Safety** — it's about financial feasibility, not admission odds."
        if lang == "en"
        else "超出預算但可能透過助學金彌補差距的學校。"
        "**Stretch 與挑戰/目標/保底分類無關** — 這是財務可行性評估，與錄取機率分開。"
    )
    st.info(
        "⚠️ **Disclaimer:** Aid figures shown (Pell grant rate) are institution-wide averages. "
        "Actual aid for your specific program may differ significantly. "
        "Institutional grant aid averages are not yet in our data pipeline — see CHANGES.md."
        if lang == "en"
        else "⚠️ **免責聲明：** 顯示的助學金比例（Pell 補助率）為學校整體平均值，"
        "你實際科系的助學金金額可能差異很大。機構助學金平均值尚未納入資料流程，詳見 CHANGES.md。"
    )
    if _n_suppressed_aid > 0:
        st.warning(
            f"ℹ️ {_n_suppressed_aid} schools had suppressed/missing aid data and cannot be fully scored for Stretch."
            if lang == "en"
            else f"ℹ️ {_n_suppressed_aid} 所學校的助學金資料被隱藏或缺失，無法完整評估 Stretch 條件。"
        )
    if _stretch_df.empty:
        st.info(
            "No schools qualify for Stretch with your current budget and filters. "
            "Stretch schools must have: match score ≥ 7.0, cost ≤ budget × 1.8, and Pell aid rate ≥ 30%."
            if lang == "en"
            else "目前預算與篩選條件下無符合 Stretch 的學校。"
            "Stretch 需滿足：配對分數 ≥ 7.0、費用 ≤ 預算 × 1.8、Pell 補助率 ≥ 30%。"
        )
    else:
        # Tier 1
        tier1 = _stretch_df[_stretch_df["stretch_tier"] == 1]
        if not tier1.empty:
            st.markdown(
                "#### 🟢 Tier 1 — Negotiable Gap (COA ≤ budget × 1.3)"
                if lang == "en"
                else "#### 🟢 第一層 — 可協商差距（費用 ≤ 預算 × 1.3）"
            )
            render_stretch_cards_2col(tier1)
        # Tier 2
        tier2 = _stretch_df[_stretch_df["stretch_tier"] == 2]
        if not tier2.empty:
            st.markdown(
                "#### 🟡 Tier 2 — Aggressive Stretch (COA 1.3×–1.8× budget)"
                if lang == "en"
                else "#### 🟡 第二層 — 積極拉伸（費用為預算 1.3×–1.8×）"
            )
            render_stretch_cards_2col(tier2)

# Unknown category (schools with no admission data)
if not unknown_df.empty:
    with st.expander(
        f"❓ {len(unknown_df)} schools with no admission data"
        if lang == "en"
        else f"❓ {len(unknown_df)} 所無錄取率資料的學校"
    ):
        render_cards_2col(unknown_df, "❓ UNKNOWN", "#9E9E9E", "")

# ── Full Ranked List ───────────────────────────────────────────────────────────
st.markdown("---")
with st.expander(
    f"📋 Full Ranked List — all {len(df)} scored schools"
    if lang == "en"
    else f"📋 完整排名清單 — 全部 {len(df)} 所評分學校"
):
    is_intl = effective_profile.get("nationality", "United States") != "United States"
    cost_col = "tuition_out" if is_intl else "net_price"

    base_cols = [
        "name", "state", "type_en", "admit_category",
        "match_score", "admit_prob", cost_col,
        "earnings_10yr", "completion_rate", "value_score",
    ]
    col_names = [
        "School", "State", "Type", "Category",
        "Match Score", "Est. Admit %",
        "Cost/yr", "10yr Earnings", "Grad Rate", "CP Score",
    ]

    # Add field-specific columns when available
    if "field_earnings" in df.columns:
        base_cols.append("field_earnings")
        col_names.append("Field Earnings")
    if "reputation_bonus" in df.columns:
        base_cols.append("reputation_bonus")
        col_names.append("Reputation Score")
    if "field_size" in df.columns:
        base_cols.append("field_size")
        col_names.append("Program Breadth")

    display_df = df[base_cols].copy()
    display_df.columns = col_names

    display_df["Est. Admit %"] = display_df["Est. Admit %"].apply(
        lambda x: f"{x * 100:.0f}%" if pd.notna(x) else "N/A"
    )
    display_df["Cost/yr"] = display_df["Cost/yr"].apply(
        lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
    )
    display_df["10yr Earnings"] = display_df["10yr Earnings"].apply(
        lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
    )
    if "Field Earnings" in display_df.columns:
        display_df["Field Earnings"] = display_df["Field Earnings"].apply(
            lambda x: fmt_usd(x) if pd.notna(x) else "—"
        )
        # Add earnings source column right after 10yr Earnings
        display_df.insert(
            display_df.columns.get_loc("Field Earnings"),
            "Earnings Source",
            display_df["Field Earnings"].apply(lambda x: "Field-specific" if x != "—" else "School-wide"),
        )
    if "Reputation Score" in display_df.columns:
        display_df["Reputation Score"] = display_df["Reputation Score"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "—"
        )
    display_df["Grad Rate"] = display_df["Grad Rate"].apply(
        lambda x: f"{x*100:.0f}%" if pd.notna(x) else "N/A"
    )
    display_df["CP Score"] = display_df["CP Score"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    display_df.index = range(1, len(display_df) + 1)
    st.dataframe(display_df, use_container_width=True)
    if target_degree_val in _GRAD_DEGREES:
        st.caption(
            "ℹ️ 10yr Earnings and Grad Rate are institution-wide (undergrad) figures. "
            "Field Earnings and Reputation Score are grad-program-specific where available."
            if lang == "en"
            else "ℹ️ 10年薪資與畢業率為學校整體（大學部）數據。科系薪資與聲望分數為研究所課程專屬數據（有資料時顯示）。"
        )

# ── Why These Schools (transparency) ──────────────────────────────────────────
st.markdown("---")
with st.expander(
    "🔍 Why These Schools? — How the algorithm works"
    if lang == "en"
    else "🔍 為什麼推薦這些學校？— 演算法說明"
):
    w = effective_profile.get("priority_weights", {})
    total_w = sum(w.values()) or 1

    st.markdown(
        "#### Your Priority Weights" if lang == "en" else "#### 你的優先排序"
    )
    _grad_label = "📈 Program Reputation" if target_degree_val in _GRAD_DEGREES else "📈 CP Value"
    weight_items = [
        (_grad_label, w.get("cp_value", 3)),
        ("🏆 Prestige", w.get("prestige", 2)),
        ("💰 Low Cost", w.get("low_cost", 3)),
        ("💼 Employment", w.get("employment", 3)),
    ]
    for label, val in weight_items:
        bar = "🟧" * int(val) + "⬜" * (5 - int(val))
        pct = f"{val / total_w * 100:.0f}%"
        st.markdown(
            f"**{label}** &nbsp; {bar} &nbsp; "
            f"<span style='color:#888;font-size:0.88rem;'>{val}/5 · {pct} of score</span>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if target_degree_val in _GRAD_DEGREES:
        st.markdown(
            f"""
#### How Match Score is Calculated — Graduate Mode ({target_degree_val})
Each school is **percentile-ranked** against all other results on four dimensions.
Scores always spread 0–10 (best school ≈ 10, worst ≈ 0).

| Dimension | Data Used | Note |
|-----------|-----------|------|
| **Program Reputation** | Lookup table of commonly ranked programs (0–1 tier) | Replaces CP Value; schools not in table are treated neutrally |
| **Prestige** | Undergrad admission rate, adjusted for grad-level | Heuristic — actual program admit rates vary widely |
| **Low Cost** | Annual cost (cheaper = better) | Out-of-state tuition for international students |
| **Employment** | Field-specific earnings if available, else school-wide 10yr | ⚠️ School-wide figures are biased by undergrad majors |

⚠️ **Graduate data limitations:** College Scorecard does not publish graduate-program-specific
admission rates or completion rates. Values shown are institution-wide proxies.
Always verify with each program's admissions office.
            """
            if lang == "en"
            else
            f"""
#### 配對分數計算方式 — 研究所模式（{target_degree_val}）
每所學校在四個維度以**百分位排名**互相比較，分數永遠分散在 0–10 之間。

| 維度 | 使用資料 | 說明 |
|------|---------|------|
| **課程聲望** | 常見排名的課程聲望對照表（0–1 分）| 取代 CP 值；不在對照表中的學校視為中性 |
| **聲望** | 大學部錄取率（已依研究所層級調整）| 啟發式估計 — 實際課程錄取率差異很大 |
| **低費用** | 年費用（越便宜排名越高）| 國際生使用外州學費 |
| **就業** | 有科系薪資時用科系薪資，否則用學校整體 10 年薪資 | ⚠️ 學校整體薪資受大學部科系影響，可能偏高 |

⚠️ **研究所資料限制：** College Scorecard 不提供研究所課程專屬的錄取率或畢業率，顯示值均為學校整體的代理指標，請向各校招生辦公室確認實際數字。
            """
        )
    else:
        st.markdown(
            """
#### How Match Score is Calculated
Each school is **percentile-ranked** against all other results on four dimensions,
so scores always spread 0–10 (the best school in your results ≈ 10, worst ≈ 0).

| Dimension | Data Used | Higher = |
|-----------|-----------|---------|
| **CP Value** | `10yr earnings ÷ net price × grad rate` | Better ROI |
| **Prestige** | `1 − admission rate` | More selective |
| **Low Cost** | Annual cost (cheaper = better rank) | Cheaper |
| **Employment** | Field-specific earnings where available, else school-wide 10yr median | Higher earnings |

Schools confirmed **not** to offer your target field lose a fixed penalty before final ranking.
            """
            if lang == "en"
            else
            """
#### 配對分數計算方式
每所學校在四個維度以**百分位排名**互相比較，所以分數永遠分散在 0–10 之間（你的結果中最好的學校 ≈ 10 分，最差 ≈ 0 分）。

| 維度 | 使用資料 | 分數越高代表 |
|------|---------|------------|
| **CP 值** | `10年薪資 ÷ 淨學費 × 畢業率` | ROI 越好 |
| **聲望** | `1 − 錄取率` | 越難進 |
| **低費用** | 年費用（越便宜排名越高）| 越便宜 |
| **就業** | 有科系薪資資料時用科系薪資，否則用學校整體 10 年薪資 | 薪資越高 |

確認**不提供**你目標科系的學校，在最終排名前會扣除固定懲罰分。
            """
    )

    st.markdown("---")
    st.markdown(
        """
#### How Admission Probability is Estimated
1. Start with the school's overall admission rate as the base probability.
2. Compare your SAT (or ACT) against the school's P25/P75 score range:
   - Above P75 → multiply base by 1.8
   - Between median and P75 → multiply by 1.3
   - Between P25 and median → no adjustment
   - Below P25 → multiply by 0.5
3. Apply a GPA multiplier (3.9+ boosts, below 2.5 reduces).
4. Classify result: **Reach** < 25% · **Target** 25–60% · **Safety** ≥ 60%

**Important limitations:** This model only uses publicly reported score distributions.
It ignores essays, recommendations, research experience, legacy status,
demonstrated interest, and many other real factors admissions offices weigh.
        """
        if lang == "en"
        else
        """
#### 錄取機率估算方式
1. 以學校公開的整體錄取率為基準。
2. 將你的 SAT（或 ACT）與學校的 P25/P75 分數區間比較：
   - 高於 P75 → 基準 × 1.8
   - 介於中位數與 P75 之間 → 基準 × 1.3
   - 介於 P25 與中位數之間 → 不調整
   - 低於 P25 → 基準 × 0.5
3. 再套用 GPA 調整係數（GPA 3.9+ 加分、低於 2.5 減分）。
4. 分類：**挑戰型** < 25% · **目標型** 25–60% · **保底型** ≥ 60%

**重要限制：** 此模型僅使用公開分數分布資料，不考慮個人文件、推薦信、研究經歷、校友優勢等真實錄取因素。
        """
    )

    st.markdown("---")
    st.markdown(
        "**Why some schools were excluded:**\n"
        "- Schools with enrollment < 200 are filtered out\n"
        "- Schools missing both earnings AND cost data are excluded (unless you enabled the toggle)\n"
        "- Results limited to 200 schools fetched based on your state/type preferences\n\n"
        "TODO: Future update will add H-1B sponsorship data, total cost calculator "
        "(tuition + living expenses), application deadline tracker, and AI Advisor integration."
        if lang == "en"
        else
        "**為什麼某些學校沒有出現：**\n"
        "- 在校人數 < 200 的學校會被過濾\n"
        "- 同時缺少薪資和費用資料的學校會被排除（除非你開啟了「包含資料缺失學校」）\n"
        "- 結果限制在根據你的州別/類型偏好抓取的 200 所學校\n\n"
        "TODO：未來版本將加入 H-1B 贊助資料、完整費用計算機（含生活費）、申請截止日提醒、及 AI 顧問整合。"
    )

# ── Earnings Data Sources ─────────────────────────────────────────────────────
st.markdown("---")
with st.expander(
    "ℹ️ About our earnings data — sources & confidence levels"
    if lang == "en"
    else "ℹ️ 薪資資料說明 — 來源與可信度"
):
    st.markdown(
        """
We use a **three-layer fallback system** to show the best available earnings estimate for each school:

| Badge | Confidence | Source | What it means |
|-------|-----------|--------|---------------|
| 🟢 **Program data** | Highest | College Scorecard | Median earnings of graduates from *this specific program at this school*. Most accurate. |
| 🟡 **National estimate** | Medium | ACS PUMS + Georgetown CEW | National median for Master's holders in this field across all schools. Not school-specific. |
| 🟠 **Occupation-based** | Lower | BLS OEWS | Median salary for occupations linked to this field. Includes all education levels. |
| 🔴 **School-wide** | Lowest | College Scorecard | Median earnings across *all* graduates of the school. Biased by engineering/CS if you're not in those fields. |

**⚠️ Important caveats:**
- 🟡 National estimates reflect the *average* Master's graduate. A top program (Harvard MBA, MIT CS)
  will likely yield significantly higher earnings than the national median.
- 🟠 BLS figures cover all degree levels — they typically *underestimate* Master's earnings for high-skill fields.
- 🔴 School-wide earnings are only shown as a last resort and are flagged in red.

**Data currency:** ACS figures estimated from 2023 data (Georgetown CEW, ACS 1-Year PUMS).
Updated annually — see `data/masters_earnings_by_field.csv`.
        """
        if lang == "en"
        else
        """
我們使用**三層備援系統**為每間學校顯示最佳的薪資估算：

| 徽章 | 可信度 | 來源 | 代表意義 |
|------|--------|------|---------|
| 🟢 **課程資料** | 最高 | College Scorecard | 該校**特定課程**畢業生的薪資中位數，最準確。 |
| 🟡 **全國估算** | 中等 | ACS PUMS + Georgetown CEW | 全國持該領域碩士學位者的薪資中位數，非特定學校。 |
| 🟠 **職業薪資** | 較低 | BLS OEWS | 該領域典型職業的薪資中位數，涵蓋所有學歷。 |
| 🔴 **學校整體** | 最低 | College Scorecard | 該校**所有科系**畢業生的整體薪資，若非工程/CS 領域會被高估。 |

**⚠️ 重要說明：**
- 🟡 全國估算反映的是*平均值*。頂尖課程（哈佛 MBA、MIT CS）的實際薪資通常遠高於全國中位數。
- 🟠 BLS 數字涵蓋所有學歷，通常低估碩士畢業生在高技能領域的薪資。
- 🔴 學校整體薪資僅作最後備選，會以紅色標示提醒。

**資料時效：** ACS 數字根據 Georgetown CEW + ACS 1-Year PUMS 2023 資料估算，每年更新。
詳見 `data/masters_earnings_by_field.csv`。
        """
    )
