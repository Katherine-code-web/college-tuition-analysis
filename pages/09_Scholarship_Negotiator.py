"""
Page 9 — Scholarship Negotiator
Multi-step wizard to estimate negotiation leverage and suggest an aid ask.

Steps:
  1. Offer Entry        — add 2–5 schools with sticker price + scholarship
  2. Target Selection   — pick ONE school to negotiate with
  3. Selectivity Tier   — compute 1–10 tier proxy per school
  4. Leverage Calc      — weighted score (peer_pressure + price_gap + profile_strength)
  5. Visualization      — bar chart + colour-coded interpretation
  6. Suggested Ask      — dollar amount + rationale bullets
  7. Action Summary     — static checklist (no email generator yet)

Deferred: email template generator (next iteration).
"""

import streamlit as st
import pandas as pd
from utils.theme import get_theme_css
from utils.sidebar import render_profile_status

st.set_page_config(
    page_title="Scholarship Negotiator",
    page_icon="💰",
    layout="wide",
)
st.markdown(get_theme_css(), unsafe_allow_html=True)

lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.markdown("### 💰 Scholarship Negotiator")
    st.caption("Estimate your leverage before emailing a financial aid office.")
    st.markdown("---")
    render_profile_status(lang)

st.title("💰 Scholarship Negotiator" if lang == "en" else "💰 獎學金協商助手")
st.markdown(
    "> ⚠️ **Disclaimer:** Typical successful negotiations yield $2k–$10k additional aid. "
    "Results not guaranteed. This tool estimates leverage based on public data only. "
    "Email template generator is coming in a future update."
    if lang == "en"
    else
    "> ⚠️ **免責聲明：** 成功的獎學金協商通常可多爭取 $2k–$10k 的助學金。"
    "結果不保證。本工具僅根據公開資料估算協商槓桿。信件範本生成器將在未來版本推出。"
)

st.markdown("---")

# ── Session state initialisation ─────────────────────────────────────────────
if "offers" not in st.session_state:
    st.session_state["offers"] = []
if "neg_target_idx" not in st.session_state:
    st.session_state["neg_target_idx"] = None
if "neg_step" not in st.session_state:
    st.session_state["neg_step"] = 1

# Pre-fill from Smart Matcher Stretch tab if available
_prefill = st.session_state.pop("negotiator_prefill", None)
if _prefill:
    # Check if this school is already in offers
    existing_names = [o["school_name"] for o in st.session_state["offers"]]
    if _prefill.get("name", "") not in existing_names:
        st.session_state["offers"].append({
            "school_name": _prefill.get("name", ""),
            "sticker_price": int(_prefill.get("cost", 0)),
            "scholarship": 0,
            "deadline": "",
        })
    st.success(
        f"Pre-filled **{_prefill.get('name','')}** from your Stretch list. "
        "Add your other competing offers below."
        if lang == "en"
        else f"已從 Stretch 清單預填 **{_prefill.get('name','')}**。請在下方加入其他競爭報價。"
    )

profile = st.session_state.get("user_profile", {})

# ── Selectivity tier helper ────────────────────────────────────────────────────

def estimate_selectivity_tier(school: dict) -> float:
    """
    Estimate a 1–10 selectivity tier per school using public proxies.
    Not an official ranking — see tooltip in UI.
    """
    adm_score = (1 - school["adm_rate"]) * 10 if school.get("adm_rate") is not None else 5
    sat_score = (
        min((school["sat_avg"] - 1000) / 60, 10)
        if school.get("sat_avg") is not None
        else 5
    )
    earn_score = (
        min(school["md_earn"] / 15000, 10)
        if school.get("md_earn") is not None
        else 5
    )
    return round(adm_score * 0.5 + sat_score * 0.3 + earn_score * 0.2, 1)


# ── Leverage calculation ───────────────────────────────────────────────────────

def calculate_leverage(target: dict, competitors: list, user_profile: dict) -> tuple[float, dict]:
    """
    Compute a 0–100 leverage score.

    Weights: peer_pressure 35 / price_gap 45 / profile_strength 20.
    If gpa_75th missing for target: skip profile_strength, scale others up
    (peer_pressure 44, price_gap 56).

    yield_concern removed — no reliable public data.
    """
    score = {"peer_pressure": 0.0, "price_gap": 0.0, "profile_strength": 0.0}
    target_tier = target.get("selectivity_tier", 5)

    for c in competitors:
        comp_tier = c.get("selectivity_tier", 5)
        if comp_tier >= target_tier - 0.5:
            score["peer_pressure"] += 17  # two competitors → maxed at 35

        target_net = (target.get("cost") or 0) - (target.get("offer") or 0)
        comp_net = (c.get("cost") or 0) - (c.get("offer") or 0)
        if comp_net < target_net and target_net > 0:
            gap_pct = (target_net - comp_net) / target_net
            score["price_gap"] += gap_pct * 45

    score["peer_pressure"] = min(score["peer_pressure"], 35)
    score["price_gap"] = min(score["price_gap"], 45)

    # Profile strength — needs target's GPA 75th percentile
    has_gpa_75th = target.get("gpa_75th") is not None
    user_gpa = user_profile.get("gpa")
    if has_gpa_75th and user_gpa and user_gpa >= target["gpa_75th"]:
        score["profile_strength"] = 20
    else:
        score["profile_strength"] = 0

    score = {k: max(v, 0) for k, v in score.items()}

    # If gpa_75th missing: scale peer_pressure and price_gap to fill the 20-pt gap
    if not has_gpa_75th:
        total_without_profile = score["peer_pressure"] + score["price_gap"]
        if total_without_profile > 0:
            # Scale proportionally: peer_pressure max 44, price_gap max 56
            score["peer_pressure"] = min(score["peer_pressure"] * 44 / 35, 44)
            score["price_gap"] = min(score["price_gap"] * 56 / 45, 56)

    total = min(sum(score.values()), 100)
    return round(total, 1), score


def _leverage_label(total: float) -> tuple[str, str, str]:
    """Return (label, color, advice) for a leverage score."""
    if total <= 30:
        return (
            "Weak" if lang == "en" else "薄弱",
            "#E8503A",
            "Negotiation unlikely to succeed. Consider accepting current offer."
            if lang == "en"
            else "協商可能不會成功，建議接受目前報價。",
        )
    elif total <= 60:
        return (
            "Moderate" if lang == "en" else "中等",
            "#FF8C42",
            "Worth trying. Expect a small increase of $2k–$5k."
            if lang == "en"
            else "值得嘗試，預計可多爭取 $2k–$5k。",
        )
    else:
        return (
            "Strong" if lang == "en" else "強勁",
            "#6BCB77",
            "Likely to succeed. Aim for $5k–$15k additional aid."
            if lang == "en"
            else "很可能成功，目標額外爭取 $5k–$15k 助學金。",
        )


def _suggested_ask(total: float, target_info: dict, competitors: list) -> tuple[int, list]:
    """
    Return (ask_amount, rationale_bullets).

    Weak: $2k–$3k max
    Moderate: 50% of price gap with best competing offer
    Strong: 80–100% of gap, capped at $15k
    """
    target_net = (target_info.get("cost") or 0) - (target_info.get("offer") or 0)
    # Best competing net cost
    best_comp_net = None
    best_comp_name = ""
    for c in competitors:
        c_net = (c.get("cost") or 0) - (c.get("offer") or 0)
        if best_comp_net is None or c_net < best_comp_net:
            best_comp_net = c_net
            best_comp_name = c.get("school_name", "competitor")
    price_gap = max(target_net - (best_comp_net or target_net), 0)

    rationale = []
    if total <= 30:
        ask = 2500
        rationale.append("Leverage is weak — a modest ask of ~$2,500 reduces friction."
                         if lang == "en" else "槓桿薄弱 — 要求約 $2,500 以減少阻力。")
    elif total <= 60:
        ask = min(int(price_gap * 0.5), 10000) if price_gap > 0 else 3000
        rationale.append(f"50% of net cost gap vs. {best_comp_name} (${price_gap:,.0f} gap)."
                         if lang == "en"
                         else f"與 {best_comp_name} 淨費用差距的 50%（差距 ${price_gap:,.0f}）。")
    else:
        ask = min(int(price_gap * 0.90), 15000) if price_gap > 0 else 5000
        rationale.append(f"Strong leverage — aim for 80–100% of net cost gap vs. {best_comp_name} (${price_gap:,.0f})."
                         if lang == "en"
                         else f"槓桿強勁 — 目標爭取與 {best_comp_name} 淨費用差距的 80–100%（${price_gap:,.0f}）。")

    # Additional rationale bullets
    target_tier = target_info.get("selectivity_tier", 5)
    for c in competitors:
        c_tier = c.get("selectivity_tier", 5)
        if c_tier >= target_tier - 0.5:
            rationale.append(f"{c.get('school_name','Competitor')} (tier {c_tier:.1f}) is at least as selective — strong negotiation signal."
                             if lang == "en"
                             else f"{c.get('school_name','競爭對手')}（第 {c_tier:.1f} 層）同樣具有選擇性 — 強協商信號。")

    user_gpa = profile.get("gpa")
    if user_gpa and target_info.get("gpa_75th") and user_gpa >= target_info["gpa_75th"]:
        rationale.append(f"Your GPA ({user_gpa:.2f}) exceeds the school's 75th percentile — profile advantage."
                         if lang == "en"
                         else f"你的 GPA（{user_gpa:.2f}）超過學校的 75th percentile — 資歷優勢。")

    return ask, rationale


# ── Step navigation ────────────────────────────────────────────────────────────
step = st.session_state["neg_step"]

# Progress indicator
step_labels = [
    "1. Add Offers",
    "2. Pick Target",
    "3. Tiers",
    "4–5. Leverage",
    "6. Ask",
    "7. Summary",
]
progress_html = "".join(
    f'<span style="background:{"#FF8C42" if i+1 == step else "#E0E0E0"};'
    f'color:{"white" if i+1 == step else "#555"};'
    f'border:2px solid #1A1A1A;border-radius:20px;padding:4px 12px;'
    f'margin:3px;font-size:0.78rem;font-weight:800;display:inline-block;">'
    f'{label}</span>'
    for i, label in enumerate(step_labels)
)
st.markdown(f'<div style="margin-bottom:12px;">{progress_html}</div>', unsafe_allow_html=True)
st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════════
# STEP 1 — Offer Entry
# ════════════════════════════════════════════════════════════════════════════════
if step == 1:
    st.subheader("Step 1 — Add Your School Offers" if lang == "en" else "步驟 1 — 新增學校報價")
    st.caption(
        "Add 2–5 schools you have (or expect) offers from. "
        "Include the sticker price and any scholarship already offered."
        if lang == "en"
        else "新增 2–5 所你已收到（或預期會收到）報價的學校，包含定價與已獲得的獎學金。"
    )

    offers = st.session_state["offers"]

    # Add school form
    with st.expander("➕ Add a School", expanded=len(offers) < 2):
        with st.form("add_offer_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                new_school = st.text_input(
                    "School Name" if lang == "en" else "學校名稱",
                    placeholder="e.g. Harvard University",
                )
                new_sticker = st.number_input(
                    "Sticker Price (annual COA, USD)" if lang == "en" else "定價（年費用，美元）",
                    min_value=0, max_value=200000, value=60000, step=1000,
                )
            with c2:
                new_scholarship = st.number_input(
                    "Scholarship Offered (USD, 0 if none)" if lang == "en" else "已獲獎學金（美元，無則填 0）",
                    min_value=0, max_value=200000, value=0, step=1000,
                )
                new_deadline = st.text_input(
                    "Decision Deadline (optional)" if lang == "en" else "決定截止日（選填）",
                    placeholder="e.g. April 30",
                )
            submitted_offer = st.form_submit_button(
                "✅ Add School" if lang == "en" else "✅ 新增學校",
                type="primary",
            )
            if submitted_offer and new_school.strip():
                if len(offers) >= 5:
                    st.warning("Maximum 5 schools." if lang == "en" else "最多新增 5 所學校。")
                else:
                    st.session_state["offers"].append({
                        "school_name": new_school.strip(),
                        "sticker_price": new_sticker,
                        "scholarship": new_scholarship,
                        "deadline": new_deadline.strip(),
                    })
                    st.rerun()

    # Display current offers
    if not offers:
        st.info(
            "No schools added yet. Add at least 2 to proceed."
            if lang == "en"
            else "尚未新增學校，請至少新增 2 所以繼續。"
        )
    else:
        st.markdown("#### Your Offers" if lang == "en" else "#### 你的報價")
        for idx, offer in enumerate(offers):
            net = offer["sticker_price"] - offer["scholarship"]
            cols = st.columns([3, 2, 2, 2, 1])
            cols[0].markdown(f"**{offer['school_name']}**")
            cols[1].markdown(f"Sticker: **${offer['sticker_price']:,}**")
            cols[2].markdown(f"Aid: **${offer['scholarship']:,}**")
            cols[3].markdown(f"Net: **${net:,}**")
            if cols[4].button("🗑️", key=f"del_{idx}", help="Remove"):
                st.session_state["offers"].pop(idx)
                st.rerun()

    st.markdown("---")
    if len(offers) >= 2:
        if st.button("Next: Pick Target →" if lang == "en" else "下一步：選擇目標 →", type="primary"):
            st.session_state["neg_step"] = 2
            st.rerun()
    else:
        st.caption(
            "Add at least 2 schools to continue."
            if lang == "en"
            else "請至少新增 2 所學校才能繼續。"
        )


# ════════════════════════════════════════════════════════════════════════════════
# STEP 2 — Target Selection
# ════════════════════════════════════════════════════════════════════════════════
elif step == 2:
    st.subheader("Step 2 — Pick Your Negotiation Target" if lang == "en" else "步驟 2 — 選擇協商目標")
    st.caption(
        "Choose ONE school to negotiate with. The others become your competing offers."
        if lang == "en"
        else "選擇一所學校作為協商目標，其餘學校將成為你的競爭報價。"
    )

    offers = st.session_state["offers"]
    school_names = [o["school_name"] for o in offers]

    default_idx = st.session_state.get("neg_target_idx") or 0
    if default_idx >= len(school_names):
        default_idx = 0

    target_choice = st.radio(
        "Select your negotiation target:" if lang == "en" else "選擇協商目標：",
        school_names,
        index=default_idx,
    )
    target_idx = school_names.index(target_choice)
    st.session_state["neg_target_idx"] = target_idx

    target_offer = offers[target_idx]
    competitors = [o for i, o in enumerate(offers) if i != target_idx]

    st.markdown("---")
    col_t, col_c = st.columns(2)
    with col_t:
        st.markdown("**🎯 Target School**")
        net_t = target_offer["sticker_price"] - target_offer["scholarship"]
        st.markdown(
            f'<div style="background:white;border:2.5px solid #FF8C42;border-radius:12px;'
            f'box-shadow:4px 4px 0px #1A1A1A;padding:16px 18px;">'
            f'<div style="font-family:Fredoka One,cursive;font-size:1.1rem;">{target_offer["school_name"]}</div>'
            f'<div style="font-size:0.85rem;color:#555;margin-top:6px;">Sticker: ${target_offer["sticker_price"]:,}</div>'
            f'<div style="font-size:0.85rem;color:#555;">Current aid: ${target_offer["scholarship"]:,}</div>'
            f'<div style="font-size:0.9rem;font-weight:800;color:#E8503A;margin-top:6px;">Net cost: ${net_t:,}/yr</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_c:
        st.markdown("**🆚 Competing Offers**")
        for comp in competitors:
            net_c = comp["sticker_price"] - comp["scholarship"]
            st.markdown(
                f'<div style="background:white;border:2px solid #1A1A1A;border-radius:10px;'
                f'padding:10px 14px;margin-bottom:8px;">'
                f'<div style="font-weight:800;">{comp["school_name"]}</div>'
                f'<div style="font-size:0.82rem;color:#555;">Net: ${net_c:,}/yr</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back" if lang == "en" else "← 返回"):
            st.session_state["neg_step"] = 1
            st.rerun()
    with c2:
        if st.button("Next: Compute Tiers →" if lang == "en" else "下一步：計算層級 →", type="primary"):
            st.session_state["neg_step"] = 3
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 3 — Selectivity Tier
# ════════════════════════════════════════════════════════════════════════════════
elif step == 3:
    st.subheader(
        "Step 3 — Selectivity Tiers (Ranking Proxy)"
        if lang == "en"
        else "步驟 3 — 選擇性層級（排名代理指標）"
    )
    st.caption(
        "Enter what you know about each school. Fields left blank will default to 5/10."
        if lang == "en"
        else "填入每所學校的已知資訊，留空欄位預設為 5/10。"
    )

    st.info(
        "**Selectivity tier (proxy):** Estimated from admission rate, test scores, and "
        "post-grad earnings. Not an official ranking. Scores are 1 (least selective) – 10 (most selective)."
        if lang == "en"
        else "**選擇性層級（代理）：** 根據錄取率、考試成績與畢業後薪資估算，非官方排名。分數 1（最不具選擇性）至 10（最具選擇性）。"
    )

    offers = st.session_state["offers"]
    target_idx = st.session_state.get("neg_target_idx", 0)

    updated_offers = []
    for i, offer in enumerate(offers):
        role = "🎯 TARGET" if i == target_idx else "🆚 Competitor"
        with st.expander(f"{role}: {offer['school_name']}", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                adm_rate = st.number_input(
                    "Admission Rate (0–1)" if lang == "en" else "錄取率（0–1）",
                    min_value=0.0, max_value=1.0,
                    value=float(offer.get("adm_rate") or 0.0),
                    step=0.01, key=f"adm_{i}",
                    help="e.g. 0.05 = 5%",
                )
            with c2:
                sat_avg = st.number_input(
                    "SAT Avg (400–1600)" if lang == "en" else "平均 SAT（400–1600）",
                    min_value=0, max_value=1600,
                    value=int(offer.get("sat_avg") or 0),
                    step=10, key=f"sat_{i}",
                    help="Leave 0 if unknown",
                )
            with c3:
                md_earn = st.number_input(
                    "Median Earnings 10yr ($)" if lang == "en" else "10年薪資中位數（$）",
                    min_value=0, max_value=500000,
                    value=int(offer.get("md_earn") or 0),
                    step=1000, key=f"earn_{i}",
                    help="Leave 0 if unknown",
                )
            with c4:
                gpa_75th = st.number_input(
                    "GPA 75th pctile (0–4)" if lang == "en" else "GPA 75th pctile（0–4）",
                    min_value=0.0, max_value=4.0,
                    value=float(offer.get("gpa_75th") or 0.0),
                    step=0.01, key=f"gpa75_{i}",
                    help="Leave 0 if unknown",
                )

            school_data = {
                "adm_rate": adm_rate if adm_rate > 0 else None,
                "sat_avg": sat_avg if sat_avg > 0 else None,
                "md_earn": md_earn if md_earn > 0 else None,
                "gpa_75th": gpa_75th if gpa_75th > 0 else None,
            }
            tier = estimate_selectivity_tier(school_data)
            st.markdown(
                f'<div style="background:#FFF8F0;border:1.5px solid #FFD166;border-radius:8px;'
                f'padding:8px 14px;display:inline-block;">'
                f'<span style="font-family:Fredoka One,cursive;font-size:1.1rem;color:#FF8C42;">'
                f'Tier: {tier}/10</span></div>',
                unsafe_allow_html=True,
            )

            updated_offer = {
                **offer,
                "adm_rate": adm_rate if adm_rate > 0 else None,
                "sat_avg": sat_avg if sat_avg > 0 else None,
                "md_earn": md_earn if md_earn > 0 else None,
                "gpa_75th": gpa_75th if gpa_75th > 0 else None,
                "selectivity_tier": tier,
                "cost": offer["sticker_price"],
                "offer": offer["scholarship"],
            }
            updated_offers.append(updated_offer)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back" if lang == "en" else "← 返回"):
            st.session_state["neg_step"] = 2
            st.rerun()
    with c2:
        if st.button("Next: Calculate Leverage →" if lang == "en" else "下一步：計算協商槓桿 →", type="primary"):
            st.session_state["offers"] = updated_offers
            st.session_state["neg_step"] = 4
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 4 + 5 — Leverage Calculation + Visualization
# ════════════════════════════════════════════════════════════════════════════════
elif step == 4:
    st.subheader(
        "Steps 4 & 5 — Leverage Score"
        if lang == "en"
        else "步驟 4 & 5 — 協商槓桿分數"
    )

    offers = st.session_state["offers"]
    target_idx = st.session_state.get("neg_target_idx", 0)
    if target_idx >= len(offers):
        st.error("Target index out of range. Please go back and re-select.")
        st.stop()

    target_info = offers[target_idx]
    competitors = [o for i, o in enumerate(offers) if i != target_idx]

    total, breakdown = calculate_leverage(target_info, competitors, profile)
    label, color, advice = _leverage_label(total)

    # Big number display
    st.markdown(
        f'<div style="background:white;border:3px solid #1A1A1A;border-radius:16px;'
        f'box-shadow:5px 5px 0px #1A1A1A;padding:24px 28px;text-align:center;margin-bottom:20px;">'
        f'<div style="font-family:Fredoka One,cursive;font-size:3rem;color:{color};line-height:1;">'
        f'{total}/100</div>'
        f'<div style="font-family:Fredoka One,cursive;font-size:1.3rem;color:{color};margin-top:4px;">'
        f'{label}</div>'
        f'<div style="font-size:0.9rem;color:#555;margin-top:8px;font-weight:700;">{advice}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Horizontal bar chart (Plotly)
    try:
        import plotly.graph_objects as go
        components = list(breakdown.keys())
        values = [round(breakdown[k], 1) for k in components]
        maxes = {
            "peer_pressure": 35,
            "price_gap": 45,
            "profile_strength": 20,
        }
        max_vals = [maxes.get(k, 20) for k in components]
        labels_map = {
            "peer_pressure": "Peer Pressure" if lang == "en" else "同儕壓力",
            "price_gap": "Price Gap" if lang == "en" else "費用差距",
            "profile_strength": "Profile Strength" if lang == "en" else "申請資歷優勢",
        }
        display_labels = [labels_map.get(k, k) for k in components]

        fig = go.Figure()
        # Background bars (max possible)
        fig.add_trace(go.Bar(
            x=max_vals, y=display_labels,
            orientation="h",
            marker_color="#F0E6D6",
            showlegend=False,
            hoverinfo="skip",
        ))
        # Actual bars
        bar_colors = [color if v > 0 else "#E0E0E0" for v in values]
        fig.add_trace(go.Bar(
            x=values, y=display_labels,
            orientation="h",
            marker_color=bar_colors,
            text=[f"{v:.0f}" for v in values],
            textposition="auto",
            showlegend=False,
            hovertemplate="%{y}: %{x}<extra></extra>",
        ))
        fig.update_layout(
            barmode="overlay",
            title=f"Leverage Breakdown — {target_info['school_name']}"
                  if lang == "en"
                  else f"協商槓桿分解 — {target_info['school_name']}",
            xaxis_title="Points" if lang == "en" else "分數",
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
            font=dict(family="Nunito", size=13),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        # Fallback if Plotly not available
        for k, v in breakdown.items():
            display_k = {"peer_pressure": "Peer Pressure", "price_gap": "Price Gap",
                         "profile_strength": "Profile Strength"}.get(k, k)
            st.markdown(f"**{display_k}:** {v:.0f} pts")

    # Breakdown table
    with st.expander("📋 Score breakdown details" if lang == "en" else "📋 分數明細"):
        bd_data = {
            "Component": [
                "Peer Pressure (max 35)" if lang == "en" else "同儕壓力（最高 35）",
                "Price Gap (max 45)" if lang == "en" else "費用差距（最高 45）",
                "Profile Strength (max 20)" if lang == "en" else "申請資歷（最高 20）",
                "Total (max 100)" if lang == "en" else "總計（最高 100）",
            ],
            "Score": [
                f"{breakdown['peer_pressure']:.0f}",
                f"{breakdown['price_gap']:.0f}",
                f"{breakdown['profile_strength']:.0f}",
                f"{total:.0f}",
            ],
        }
        st.dataframe(pd.DataFrame(bd_data), use_container_width=True, hide_index=True)

    st.session_state["_leverage_total"] = total
    st.session_state["_leverage_breakdown"] = breakdown

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back" if lang == "en" else "← 返回"):
            st.session_state["neg_step"] = 3
            st.rerun()
    with c2:
        if st.button("Next: Suggested Ask →" if lang == "en" else "下一步：建議要求金額 →", type="primary"):
            st.session_state["neg_step"] = 5
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 6 — Suggested Ask
# ════════════════════════════════════════════════════════════════════════════════
elif step == 5:
    st.subheader(
        "Step 6 — Suggested Ask Amount"
        if lang == "en"
        else "步驟 6 — 建議要求金額"
    )

    offers = st.session_state["offers"]
    target_idx = st.session_state.get("neg_target_idx", 0)
    target_info = offers[target_idx]
    competitors = [o for i, o in enumerate(offers) if i != target_idx]
    total = st.session_state.get("_leverage_total", 0)
    label, color, _ = _leverage_label(total)

    ask, rationale = _suggested_ask(total, target_info, competitors)

    st.markdown(
        f'<div style="background:white;border:3px solid #1A1A1A;border-radius:16px;'
        f'box-shadow:5px 5px 0px #1A1A1A;padding:24px 28px;margin-bottom:20px;">'
        f'<div style="font-size:0.85rem;color:#888;font-weight:800;">SUGGESTED ADDITIONAL ASK</div>'
        f'<div style="font-family:Fredoka One,cursive;font-size:2.5rem;color:{color};line-height:1.1;">'
        f'${ask:,}</div>'
        f'<div style="font-size:0.9rem;color:#555;margin-top:6px;font-weight:700;">'
        f'Leverage: {label} ({total}/100)</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Why this amount?" if lang == "en" else "#### 為什麼是這個金額？")
    for bullet in rationale:
        st.markdown(f"- {bullet}")

    st.session_state["_suggested_ask"] = ask
    st.session_state["_rationale"] = rationale

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back" if lang == "en" else "← 返回"):
            st.session_state["neg_step"] = 4
            st.rerun()
    with c2:
        if st.button("Next: Action Summary →" if lang == "en" else "下一步：行動摘要 →", type="primary"):
            st.session_state["neg_step"] = 6
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 7 — Action Summary
# ════════════════════════════════════════════════════════════════════════════════
elif step == 6:
    st.subheader(
        "Step 7 — Action Summary"
        if lang == "en"
        else "步驟 7 — 行動摘要"
    )

    offers = st.session_state["offers"]
    target_idx = st.session_state.get("neg_target_idx", 0)
    target_info = offers[target_idx]
    competitors = [o for i, o in enumerate(offers) if i != target_idx]
    total = st.session_state.get("_leverage_total", 0)
    ask = st.session_state.get("_suggested_ask", 0)
    rationale = st.session_state.get("_rationale", [])
    label, color, advice = _leverage_label(total)

    comp_names = " + ".join(c.get("school_name", "") for c in competitors)

    checklist_html = f"""
<div style="background:white;border:2.5px solid #1A1A1A;border-radius:16px;
    box-shadow:5px 5px 0px #1A1A1A;padding:24px 28px;">

  <div style="font-family:Fredoka One,cursive;font-size:1.3rem;margin-bottom:16px;">
    📋 {'Action Summary' if lang == 'en' else '行動摘要'} — {target_info.get('school_name','')}
  </div>

  <div style="margin-bottom:12px;">
    <span style="background:{color};color:white;border:2px solid #1A1A1A;border-radius:6px;
        padding:4px 12px;font-weight:800;font-size:0.9rem;">
      ✅ {'Leverage Score' if lang == 'en' else '槓桿分數'}: {total}/100 ({label})
    </span>
  </div>

  <div style="margin-bottom:12px;">
    <span style="background:#FFD166;border:2px solid #1A1A1A;border-radius:6px;
        padding:4px 12px;font-weight:800;font-size:0.9rem;">
      ✅ {'Recommended Ask' if lang == 'en' else '建議要求金額'}: ${ask:,}
    </span>
  </div>

  <div style="border-top:1.5px dashed #E0E0E0;padding-top:16px;margin-top:12px;">
    <div style="font-weight:800;margin-bottom:8px;">
      📋 {'Next Steps' if lang == 'en' else '下一步'}:
    </div>
    <ul style="margin:0;padding-left:20px;line-height:2;">
      <li>{'Email your target school\'s financial aid office within 48 hours.' if lang == 'en' else '在 48 小時內寄信給目標學校的財務援助辦公室。'}</li>
      <li>{'Mention competing offer(s) by name and amount: ' + comp_names if lang == 'en' else '在信中具名提及競爭報價及金額：' + comp_names}</li>
      <li>{'Keep tone grateful and professional.' if lang == 'en' else '保持感謝且專業的語氣。'}</li>
      <li>{'Ask for a specific additional amount (${:,}).'.format(ask) if lang == 'en' else '要求具體的額外金額（${:,}）。'.format(ask)}</li>
      <li style="color:#888;">{'📧 Email template generator — coming in next update.' if lang == 'en' else '📧 信件範本生成器 — 將在下次更新推出。'}</li>
    </ul>
  </div>
</div>
"""
    st.markdown(checklist_html, unsafe_allow_html=True)

    st.markdown("---")

    # Rationale recap
    if rationale:
        with st.expander(
            "💡 Why this strategy?" if lang == "en" else "💡 為什麼是這個策略？"
        ):
            for r in rationale:
                st.markdown(f"- {r}")

    st.markdown(
        "> ⚠️ **Disclaimer:** Typical successful negotiations yield $2k–$10k additional aid. "
        "Results not guaranteed. This tool estimates leverage based on public data only."
        if lang == "en"
        else "> ⚠️ **免責聲明：** 成功的獎學金協商通常可多爭取 $2k–$10k。"
        "結果不保證。本工具僅根據公開資料估算協商槓桿。"
    )

    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("← Back" if lang == "en" else "← 返回"):
            st.session_state["neg_step"] = 5
            st.rerun()
    with c2:
        if st.button("🔄 Start Over" if lang == "en" else "🔄 重新開始"):
            st.session_state["offers"] = []
            st.session_state["neg_target_idx"] = None
            st.session_state["neg_step"] = 1
            st.session_state.pop("_leverage_total", None)
            st.session_state.pop("_leverage_breakdown", None)
            st.session_state.pop("_suggested_ask", None)
            st.session_state.pop("_rationale", None)
            st.rerun()
    with c3:
        if st.button(
            "🎯 Back to Smart Matcher" if lang == "en" else "🎯 返回 Smart Matcher",
            type="primary",
        ):
            st.switch_page("pages/8_Smart_Matcher.py")
