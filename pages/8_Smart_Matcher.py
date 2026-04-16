"""
Page 8 — Smart School Matcher
Personalized Reach / Target / Safety school recommendations based on user profile.
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

# Build an effective profile with sidebar overrides
effective_profile = {**profile, "annual_budget": budget_override}

# Derive CIP 2-digit prefix from profile field selection
target_cip = effective_profile.get("target_field_cip", "")
cip_prefix = target_cip[:2] if target_cip else ""

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
    )
    # Fallback 1: drop state filter if too few results
    if len(raw) < 10 and preferred_states:
        raw = fetch_candidate_schools(
            states=(),
            ownership=ownership_code,
            cip_2digit=cip_prefix,
            per_page=100,
            n_pages=2,
        )
    # Fallback 2: drop CIP filter too (API may not support it for all fields)
    if len(raw) < 10:
        raw = fetch_candidate_schools(
            states=preferred_states or (),
            ownership=ownership_code,
            cip_2digit="",
            per_page=100,
            n_pages=2,
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

# ── Budget hard cap: exclude schools > budget × 1.2 ──────────────────────────
_budget = budget_override or 50000
_is_intl = effective_profile.get("nationality", "United States") != "United States"
df["effective_price"] = df["tuition_out"].fillna(df["net_price"]) if _is_intl else df["net_price"]
# Keep schools that either have no price data OR are within 1.2× budget
_within_budget = df["effective_price"].isna() | (df["effective_price"] <= _budget * 1.2)
df = df[_within_budget].copy()

if not include_no_data:
    df = df.dropna(subset=["earnings_10yr", "net_price"])

if df.empty:
    st.error(
        "No schools match your budget and data requirements. "
        "Try increasing your annual budget in the sidebar or toggle "
        "'Include schools with missing data'."
        if lang == "en"
        else "找不到符合預算且有完整資料的學校。請在左側提高年預算，或開啟「包含資料缺失學校」。"
    )
    st.stop()

# ── Fetch field-specific earnings BEFORE scoring ──────────────────────────────
# This lets score_schools_df use field_earnings in the employment dimension
# so the percentile ranking reflects your actual target field.
field_earn_map: dict[int, float] = {}
field_present_map: dict[int, bool] = {}
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
                matching = [
                    p for p in programs
                    if str(p.get("cip_code", ""))[:2] == cip_prefix
                    and p.get("median_earnings")
                ]
                if matching:
                    field_earn_map[school_id] = max(p["median_earnings"] for p in matching)
                    field_present_map[school_id] = True
                else:
                    field_present_map[school_id] = False
            except Exception:
                pass

    df["field_earnings"] = df["id"].apply(
        lambda x: field_earn_map.get(int(x)) if pd.notna(x) else None
    )
    df["has_target_field"] = df["id"].apply(
        lambda x: field_present_map.get(int(x)) if pd.notna(x) else None
    )

df = score_schools_df(effective_profile, df)
df = df.sort_values("match_score", ascending=False).reset_index(drop=True)

# Split into categories
reach_df = df[df["admit_category"] == "Reach"].head(5)
target_df = df[df["admit_category"] == "Target"].head(5)
safety_df = df[df["admit_category"] == "Safety"].head(5)
unknown_df = df[df["admit_category"] == "Unknown"].head(3)

field_label = field_override if lang == "en" else field_override
n_with_field = int(df["has_target_field"].sum()) if "has_target_field" in df.columns else len(df)
st.markdown(
    f"**{len(df)} schools scored** — {n_with_field} offer **{field_label}** programs."
    if lang == "en"
    else f"**已評分 {len(df)} 所學校** — {n_with_field} 所提供「{field_label}」科系。"
)

# Show credential hint if no field data found
if cip_prefix and "has_target_field" in df.columns and n_with_field == 0:
    hint = get_field_hint(cip_prefix, lang)
    if hint:
        st.warning(hint)
    else:
        st.warning(
            f"⚠️ No schools in results have confirmed **{field_label}** program data. "
            "Schools below are ranked by overall fit instead."
            if lang == "en"
            else f"⚠️ 結果中沒有學校有確認的「{field_label}」科系資料，以整體條件排名取代。"
        )

# ── School Card Helper ─────────────────────────────────────────────────────────

def school_card(row: dict, category_label: str, category_color: str) -> str:
    """Return HTML for a single school card."""
    name = row.get("name", "Unknown")
    location = f"{row.get('city', '')}, {row.get('state', '')}"
    school_type = row.get("type_en", "")
    match_score = row.get("match_score", 0)
    admit_prob = row.get("admit_prob")
    prob_str = (
        f"{admit_prob * 100:.0f}% admit chance"
        if admit_prob is not None
        else "N/A"
    )

    is_intl = effective_profile.get("nationality", "United States") != "United States"
    cost = (row.get("tuition_out") if is_intl else None) or row.get("net_price")
    cost_str = fmt_usd(cost) if cost else "N/A"
    cost_label = (
        ("Out-of-state tuition" if is_intl else "Net price (after aid)")
        if lang == "en"
        else ("外州學費" if is_intl else "淨學費（助學金後）")
    )

    field_earn = row.get("field_earnings")
    has_field = row.get("has_target_field")
    if field_earn:
        earn_str = fmt_usd(field_earn)
        earn_note = " <span style='color:#2E7D32;font-size:0.75rem;'>(your field)</span>"
    else:
        earn_str = fmt_usd(row.get("earnings_10yr"))
        earn_note = ""
    grad_str = fmt_pct(row.get("completion_rate"))
    budget_text = row.get("budget_fit_text", "")
    budget_color = row.get("budget_fit_color", "#555")

    field_tag = ""
    if has_field is True:
        field_tag = (
            '<span style="background:#DDFAE4;border:1.5px solid #6BCB77;border-radius:20px;'
            'padding:3px 10px;font-size:0.75rem;font-weight:800;">✓ Offers your field</span>'
        )
    elif has_field is False:
        field_tag = (
            '<span style="background:#FFF3E8;border:1.5px solid #FF8C42;border-radius:20px;'
            'padding:3px 10px;font-size:0.75rem;font-weight:800;">⚠️ Field data N/A</span>'
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
      color:#1A1A1A;line-height:1.3;margin-bottom:4px;">{name}</div>
  <div style="font-size:0.83rem;color:#777;margin-bottom:14px;">
    📍 {location} &nbsp;·&nbsp; {school_type}
  </div>

  <!-- Match score + admit prob -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px;">
    <div style="background:#FFF8F0;border:1.5px solid #FFD166;border-radius:10px;padding:10px 12px;">
      <div style="font-size:0.72rem;color:#888;margin-bottom:2px;">
        {'Match Score' if lang == 'en' else '配對分數'}
      </div>
      <div style="font-family:'Fredoka One',cursive;font-size:1.3rem;color:#FF8C42;line-height:1;">
        {match_score} <span style="font-size:0.85rem;">/10</span>
      </div>
      <div style="font-size:0.82rem;color:#FFB347;">{stars}</div>
    </div>
    <div style="background:#F8F8FF;border:1.5px solid #C5C5F0;border-radius:10px;padding:10px 12px;">
      <div style="font-size:0.72rem;color:#888;margin-bottom:2px;">
        {'Est. Admit' if lang == 'en' else '估算錄取率'}
      </div>
      <div style="font-family:'Fredoka One',cursive;font-size:1.15rem;color:#1A1A1A;line-height:1.2;">
        {prob_str}
      </div>
    </div>
  </div>

  <!-- Key metrics -->
  <div style="border-top:1.5px dashed #E0E0E0;padding-top:12px;margin-bottom:12px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
      <div>
        <div style="font-size:0.72rem;color:#888;">
          💰 {cost_label}
        </div>
        <div style="font-size:0.92rem;font-weight:800;color:#1A1A1A;">{cost_str}</div>
      </div>
      <div>
        <div style="font-size:0.72rem;color:#888;">
          💼 {'10yr Earnings' if lang == 'en' else '10年後薪資'}
        </div>
        <div style="font-size:0.92rem;font-weight:800;color:#1A1A1A;">
          {earn_str}{earn_note}
        </div>
      </div>
      <div>
        <div style="font-size:0.72rem;color:#888;">
          🎓 {'Grad Rate' if lang == 'en' else '畢業率'}
        </div>
        <div style="font-size:0.92rem;font-weight:800;color:#1A1A1A;">{grad_str}</div>
      </div>
      <div>
        <div style="font-size:0.72rem;color:#888;">
          📊 {'Budget fit' if lang == 'en' else '預算符合度'}
        </div>
        <div style="font-size:0.85rem;font-weight:800;color:{budget_color};">{budget_text}</div>
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


# ── Tabs: Reach / Target / Safety ─────────────────────────────────────────────
st.markdown("---")

tab_reach, tab_target, tab_safety = st.tabs([
    f"🎯 Reach  ({len(reach_df)})" if lang == "en" else f"🎯 挑戰型 ({len(reach_df)})",
    f"✓ Target  ({len(target_df)})" if lang == "en" else f"✓ 目標型 ({len(target_df)})",
    f"🛡️ Safety  ({len(safety_df)})" if lang == "en" else f"🛡️ 保底型 ({len(safety_df)})",
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
    display_df = df[[
        "name", "state", "type_en", "admit_category",
        "match_score", "admit_prob",
        "tuition_out" if is_intl else "net_price",
        "earnings_10yr", "completion_rate", "value_score",
    ]].copy()

    display_df.columns = [
        "School", "State", "Type", "Category",
        "Match Score", "Est. Admit %",
        "Cost/yr", "10yr Earnings", "Grad Rate", "CP Score",
    ]
    display_df["Est. Admit %"] = display_df["Est. Admit %"].apply(
        lambda x: f"{x * 100:.0f}%" if pd.notna(x) else "N/A"
    )
    display_df["Cost/yr"] = display_df["Cost/yr"].apply(
        lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
    )
    display_df["10yr Earnings"] = display_df["10yr Earnings"].apply(
        lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
    )
    display_df["Grad Rate"] = display_df["Grad Rate"].apply(
        lambda x: f"{x*100:.0f}%" if pd.notna(x) else "N/A"
    )
    display_df["CP Score"] = display_df["CP Score"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )
    display_df.index = range(1, len(display_df) + 1)
    st.dataframe(display_df, use_container_width=True)

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
    weight_items = [
        ("📈 CP Value", w.get("cp_value", 3)),
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
