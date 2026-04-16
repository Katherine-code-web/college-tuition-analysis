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

if not include_no_data:
    df = df.dropna(subset=["earnings_10yr", "net_price"])

if df.empty:
    st.warning(
        "All matched schools are missing earnings/cost data. "
        "Toggle 'Include schools with missing data' in the sidebar."
        if lang == "en"
        else "所有符合條件的學校都缺少收入/費用資料。請在左側選單開啟「包含資料缺失學校」。"
    )
    st.stop()

df = score_schools_df(effective_profile, df)
df = df.sort_values("match_score", ascending=False).reset_index(drop=True)

# ── Field-specific re-scoring ─────────────────────────────────────────────────
# Fetch program-level earnings for the user's target field in top 25 schools.
# Uses cached get_school_programs, so slow only on first run.
if cip_prefix:
    with st.spinner(
        f"🎓 Checking {field_override} program data for top schools..."
        if lang == "en"
        else f"🎓 查詢各學校「{field_override}」科系薪資資料..."
    ):
        top_ids = df.head(25)["id"].dropna().astype(int).tolist()
        field_earn_map: dict[int, float] = {}
        field_present_map: dict[int, bool] = {}

        for school_id in top_ids:
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

    # Apply field-specific adjustment to match scores
    w_employment = effective_profile.get("priority_weights", {}).get("employment", 2)
    total_w = sum(effective_profile.get("priority_weights", {}).values()) or 1
    employ_weight_share = w_employment / total_w  # fraction of score from employment

    def _adjust_score(row: pd.Series) -> float:
        sid = int(row["id"]) if pd.notna(row.get("id")) else None
        base = row["match_score"]
        if sid is None:
            return base
        # Big penalty if school doesn't offer the user's field at all
        if field_present_map.get(sid) is False:
            return max(0.0, base - 2.5)
        # Recalculate employment component with field-specific earnings
        if sid in field_earn_map:
            overall_earn = row.get("earnings_10yr") or 50000
            field_earn = field_earn_map[sid]
            old_employ = min(overall_earn / 120000, 1.0)
            new_employ = min(field_earn / 120000, 1.0)
            delta = (new_employ - old_employ) * employ_weight_share * 10
            return round(min(10.0, max(0.0, base + delta)), 2)
        return base

    df["match_score"] = df.apply(_adjust_score, axis=1)
    df["field_earnings"] = df["id"].apply(
        lambda x: field_earn_map.get(int(x)) if pd.notna(x) else None
    )
    df["has_target_field"] = df["id"].apply(
        lambda x: field_present_map.get(int(x)) if pd.notna(x) else None
    )
    df = df.sort_values("match_score", ascending=False).reset_index(drop=True)

# Split into categories
reach_df = df[df["admit_category"] == "Reach"].head(5)
target_df = df[df["admit_category"] == "Target"].head(5)
safety_df = df[df["admit_category"] == "Safety"].head(5)
unknown_df = df[df["admit_category"] == "Unknown"].head(3)

field_label = field_override if lang == "en" else field_override
n_with_field = int(df.get("has_target_field", pd.Series()).sum()) if "has_target_field" in df.columns else len(df)
st.markdown(
    f"**{len(df)} schools scored** — {n_with_field} offer **{field_label}** programs."
    if lang == "en"
    else f"**已評分 {len(df)} 所學校** — {n_with_field} 所提供「{field_label}」科系。"
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
        f"~{admit_prob * 100:.0f}% (est.)"
        if admit_prob is not None
        else "N/A (open / no data)"
    )

    is_intl = effective_profile.get("nationality", "United States") != "United States"
    cost = (row.get("tuition_out") if is_intl else None) or row.get("net_price")
    cost_str = fmt_usd(cost) if cost else "N/A"
    cost_label = (
        ("Out-of-state tuition" if is_intl else "Net price (after aid)")
        if lang == "en"
        else ("外州學費" if is_intl else "淨學費（助學金後）")
    )

    # Show field-specific earnings if available, otherwise school-wide
    field_earn = row.get("field_earnings")
    has_field = row.get("has_target_field")
    if field_earn:
        earn_str = f"{fmt_usd(field_earn)} <span style='font-size:0.72rem;color:#2E7D32;'>(your field)</span>"
    else:
        earn_str = fmt_usd(row.get("earnings_10yr"))
    grad_str = fmt_pct(row.get("completion_rate"))
    budget_text = row.get("budget_fit_text", "")
    budget_color = row.get("budget_fit_color", "#555")
    field_tag = (
        f'<span style="background:#DDFAE4;border:1.5px solid #6BCB77;border-radius:6px;'
        f'padding:2px 7px;font-size:0.72rem;margin-right:4px;">✓ Offers your field</span>'
        if has_field is True else (
        f'<span style="background:#FFF3E8;border:1.5px solid #FF8C42;border-radius:6px;'
        f'padding:2px 7px;font-size:0.72rem;margin-right:4px;">⚠️ Field data N/A</span>'
        if has_field is False else ""
        )
    )

    # Star rating bar for match score
    filled = round(match_score / 2)  # 0-10 → 0-5 stars
    stars = "★" * filled + "☆" * (5 - filled)

    url = row.get("url", "")
    url_html = (
        f'<a href="http://{url}" target="_blank" style="'
        f'background:#4D96FF;color:white;border:2px solid #1A1A1A;border-radius:8px;'
        f'padding:4px 10px;font-size:0.78rem;text-decoration:none;margin-right:6px;">'
        f'{"View School" if lang == "en" else "查看學校"}</a>'
        if url else ""
    )

    return f"""
<div style="background:white;border:2.5px solid #1A1A1A;border-radius:14px;
    box-shadow:4px 4px 0px #1A1A1A;padding:16px 18px;margin-bottom:12px;">

  <div style="display:inline-block;background:{category_color};color:white;
      font-size:0.72rem;font-weight:800;letter-spacing:1.5px;
      border:2px solid #1A1A1A;border-radius:6px;padding:2px 8px;margin-bottom:6px;">
    {category_label}
  </div>

  <div style="font-family:'Fredoka One',cursive;font-size:1.1rem;
      color:#1A1A1A;line-height:1.3;margin-bottom:2px;">{name}</div>
  <div style="font-size:0.8rem;color:#666;margin-bottom:8px;">
    {location} · {school_type}
  </div>

  <div style="display:flex;gap:16px;margin-bottom:8px;flex-wrap:wrap;">
    <div>
      <div style="font-size:0.72rem;color:#888;">Match Score</div>
      <div style="font-family:'Fredoka One',cursive;font-size:1.2rem;color:#FF8C42;">
        {match_score} / 10
        <span style="font-size:0.85rem;color:#FFB347;">{stars}</span>
      </div>
    </div>
    <div>
      <div style="font-size:0.72rem;color:#888;">{"Est. Admit" if lang == "en" else "估算錄取率"}</div>
      <div style="font-weight:800;font-size:0.92rem;">{prob_str}</div>
    </div>
  </div>

  <div style="font-size:0.82rem;margin-bottom:4px;">
    💰 <b>{cost_label}:</b> {cost_str}
  </div>
  <div style="font-size:0.82rem;margin-bottom:4px;">
    💼 <b>{"10yr Earnings" if lang == "en" else "10年後薪資"}:</b> {earn_str}
  </div>
  <div style="font-size:0.82rem;margin-bottom:8px;">
    🎓 <b>{"Grad Rate" if lang == "en" else "畢業率"}:</b> {grad_str}
  </div>

  <div style="font-size:0.82rem;font-weight:800;color:{budget_color};margin-bottom:6px;">
    {budget_text}
  </div>
  <div style="margin-bottom:10px;">{field_tag}</div>

  <div>{url_html}</div>
</div>
"""


def render_category_column(category_df, label, color, empty_msg):
    if category_df.empty:
        st.caption(empty_msg)
        return
    for _, row in category_df.iterrows():
        st.markdown(school_card(row.to_dict(), label, color), unsafe_allow_html=True)


# ── Three-Column Display ───────────────────────────────────────────────────────
st.markdown("---")

col_reach, col_target, col_safety = st.columns(3)

with col_reach:
    st.markdown(
        f'<div style="background:#E8503A;color:white;border:2.5px solid #1A1A1A;'
        f'border-radius:10px;padding:8px 14px;font-family:Fredoka One,cursive;'
        f'font-size:1.1rem;margin-bottom:12px;">🎯 Reach Schools ({len(reach_df)})</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "High ambition — low admit probability but strong match."
        if lang == "en"
        else "挑戰型 — 錄取機率較低，但條件契合度高。"
    )
    render_category_column(
        reach_df, "🎯 REACH", "#E8503A",
        "No reach schools found with current filters."
        if lang == "en" else "目前篩選條件下沒有挑戰型學校。",
    )

with col_target:
    st.markdown(
        f'<div style="background:#FF8C42;color:white;border:2.5px solid #1A1A1A;'
        f'border-radius:10px;padding:8px 14px;font-family:Fredoka One,cursive;'
        f'font-size:1.1rem;margin-bottom:12px;">✓ Target Schools ({len(target_df)})</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Balanced — realistic admit chance, good overall fit."
        if lang == "en"
        else "目標型 — 錄取機率合理，整體條件相符。"
    )
    render_category_column(
        target_df, "✓ TARGET", "#FF8C42",
        "No target schools found with current filters."
        if lang == "en" else "目前篩選條件下沒有目標型學校。",
    )

with col_safety:
    st.markdown(
        f'<div style="background:#6BCB77;color:white;border:2.5px solid #1A1A1A;'
        f'border-radius:10px;padding:8px 14px;font-family:Fredoka One,cursive;'
        f'font-size:1.1rem;margin-bottom:12px;">🛡️ Safety Schools ({len(safety_df)})</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Likely admit — strong acceptance probability."
        if lang == "en"
        else "保底型 — 錄取機率高，建議作為保底選項。"
    )
    render_category_column(
        safety_df, "🛡️ SAFETY", "#6BCB77",
        "No safety schools found with current filters."
        if lang == "en" else "目前篩選條件下沒有保底型學校。",
    )

# Show "Unknown" schools if any (no admission data)
if not unknown_df.empty:
    with st.expander(
        f"❓ Schools with no admission data ({len(unknown_df)})"
        if lang == "en"
        else f"❓ 無錄取率資料的學校（{len(unknown_df)} 所）"
    ):
        render_category_column(unknown_df, "❓ UNKNOWN", "#9E9E9E", "")

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
    pc1, pc2, pc3, pc4 = st.columns(4)
    metrics = [
        ("📈 CP Value", w.get("cp_value", 3)),
        ("🏆 Prestige", w.get("prestige", 2)),
        ("💰 Low Cost", w.get("low_cost", 3)),
        ("💼 Employment", w.get("employment", 3)),
    ]
    for col, (label, val) in zip([pc1, pc2, pc3, pc4], metrics):
        col.metric(label, f"{val}/5", f"{val/total_w*100:.0f}% weight")

    st.markdown("---")
    st.markdown(
        """
#### How Match Score is Calculated
Each school is rated 0–1 on four dimensions, then combined using your weights:

| Dimension | Data Used | Higher = |
|-----------|-----------|---------|
| **CP Value** | `10yr earnings ÷ net price × grad rate` (capped at 10) | Better ROI |
| **Prestige** | `1 − admission rate` | More selective |
| **Low Cost** | How well cost fits within your budget | Cheaper |
| **Employment** | Median 10yr earnings (capped at $120k) | Higher earnings |

Final score = weighted average × 10, displayed as 0–10.
        """
        if lang == "en"
        else
        """
#### 配對分數計算方式
每所學校在四個維度各得 0–1 分，再依你的優先權重加權平均：

| 維度 | 使用資料 | 分數越高代表 |
|------|---------|------------|
| **CP 值** | `10年薪資 ÷ 淨學費 × 畢業率`（上限 10）| ROI 越好 |
| **聲望** | `1 − 錄取率` | 越難進 |
| **低費用** | 費用與你的預算的差距 | 越便宜 |
| **就業** | 10 年後中位薪資（上限 $120k）| 薪資越高 |

最終分數 = 加權平均 × 10，以 0–10 分顯示。
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
