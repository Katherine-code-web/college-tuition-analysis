"""
Page 6 — Major Explorer
Compare the same field of study across multiple schools.
Includes cross-school earnings ranking and a Graduate Premium Calculator.
"""

import streamlit as st
from utils.theme import get_theme_css
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.translations import t
from utils.api import search_schools, results_to_df, fmt_usd, fmt_pct, get_school_programs
from utils.calculations import (
    enrich_df, programs_to_df, get_cp_animal,
    CIP_CATEGORIES, CIP_CATEGORIES_ZH,
    CRED_LEVEL_MAP, CRED_LEVEL_MAP_ZH,
    CRED_LEVEL_ORDER,
)

st.set_page_config(page_title="Major Explorer", page_icon="📚", layout="wide")
st.markdown(get_theme_css(), unsafe_allow_html=True)

lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.caption(t("data_source", lang))

st.title("📚 " + t("major_title", lang))
st.markdown(t("major_desc", lang))
st.markdown("---")

# ── Session state ─────────────────────────────────────────────────────────────
if "major_schools" not in st.session_state:
    st.session_state.major_schools = []
if "major_search_results" not in st.session_state:
    st.session_state.major_search_results = []
if "major_program_data" not in st.session_state:
    st.session_state.major_program_data = {}

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Add schools
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("1️⃣ " + t("major_search_school", lang))

add_q = st.text_input(
    "school search",
    label_visibility="collapsed",
    placeholder=t("search_to_add", lang),
    key="major_add_input",
)
do_add_search = st.button("🔍 " + t("search", lang), key="major_search_btn", type="primary")

if do_add_search and add_q:
    with st.spinner(t("loading", lang)):
        results, _ = search_schools(name=add_q, per_page=8)
    if results:
        df_r = results_to_df(results)
        df_r = enrich_df(df_r)
        st.session_state.major_search_results = df_r.to_dict("records")
    else:
        st.session_state.major_search_results = []
        st.warning(t("no_results", lang))

if st.session_state.major_search_results:
    already_ids = {s["id"] for s in st.session_state.major_schools}
    res_cols = st.columns(2)
    for i, sch in enumerate(st.session_state.major_search_results[:8]):
        with res_cols[i % 2]:
            is_added = sch["id"] in already_ids
            is_full = len(st.session_state.major_schools) >= 5
            vs = sch.get("value_score")
            btn_help = (
                f"{sch.get('city','')}, {sch.get('state','')}  ·  "
                f"{fmt_usd(sch.get('net_price'))}/yr  ·  CP {vs:.1f}" if vs else ""
            )
            if st.button(
                "✓ Added" if is_added else f"+ {sch['name']}",
                key=f"major_add_{sch['id']}",
                disabled=is_added or is_full,
                use_container_width=True,
                help=btn_help,
            ):
                st.session_state.major_schools.append(sch)
                st.rerun()

# Show added schools
if st.session_state.major_schools:
    st.markdown("**" + t("major_school_list", lang) + "**")
    tag_cols = st.columns(min(len(st.session_state.major_schools), 5))
    for idx, sch in enumerate(st.session_state.major_schools):
        with tag_cols[idx]:
            animal = get_cp_animal(sch.get("value_score"))
            st.markdown(f"""
            <div style="background:{animal['bg']};border:2px solid #1A1A1A;border-radius:10px;
                        padding:8px 10px;text-align:center;">
                <div style="font-size:1.4rem;">{animal['emoji']}</div>
                <div style="font-family:'Fredoka One',cursive;font-size:0.8rem;margin-top:2px;">{sch['name'][:22]}</div>
                <div style="font-size:0.7rem;color:#555;">{sch.get('state','')}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("✕", key=f"major_rm_{idx}_{sch['id']}", use_container_width=True):
                st.session_state.major_schools.pop(idx)
                st.session_state.major_program_data = {}
                st.rerun()

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("🗑 " + ("Clear all" if lang == "en" else "清除全部"), key="major_clear_all"):
            st.session_state.major_schools = []
            st.session_state.major_program_data = {}
            st.rerun()

if len(st.session_state.major_schools) == 0:
    st.info(
        "Add at least one school above to begin exploring programs."
        if lang == "en"
        else "請先新增至少一所學校以開始探索科系資料。"
    )
    st.stop()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Select Field of Study + Credential Level
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("2️⃣ " + t("major_filter_field", lang))

cip_cat_labels = CIP_CATEGORIES if lang == "en" else CIP_CATEGORIES_ZH
cip_options = {
    ("All Fields" if lang == "en" else "全部科系"): None,
    **{f"{k} — {v}": k for k, v in cip_cat_labels.items()},
}
selected_cip_label = st.selectbox(
    t("major_filter_field", lang),
    list(cip_options.keys()),
    key="major_cip_select",
    label_visibility="collapsed",
)
selected_cip_2digit = cip_options[selected_cip_label]

cred_map = CRED_LEVEL_MAP if lang == "en" else CRED_LEVEL_MAP_ZH
cred_filter_options = {
    ("All Levels" if lang == "en" else "全部層級"): None,
    **{v: k for k, v in cred_map.items()},
}
c_left, c_right = st.columns([2, 3])
with c_left:
    selected_cred_label = st.selectbox(
        t("major_filter_cred", lang),
        list(cred_filter_options.keys()),
        key="major_cred_select",
    )
selected_cred_level = cred_filter_options[selected_cred_label]

# Load program data
load_clicked = st.button(
    "🔬 " + ("Load Program Data" if lang == "en" else "載入科系資料"),
    key="major_load_btn",
    type="primary",
)

if load_clicked:
    st.session_state.major_program_data = {}
    with st.spinner(t("programs_loading", lang)):
        for sch in st.session_state.major_schools:
            sid = sch.get("id")
            if sid:
                raw = get_school_programs(int(sid))
                if raw:
                    pdf = programs_to_df(
                        raw,
                        school_net_price=sch.get("net_price"),
                        school_completion_rate=sch.get("completion_rate"),
                    )
                    pdf["school_name"] = sch["name"]
                    pdf["school_net_price"] = sch.get("net_price")
                    st.session_state.major_program_data[sch["name"]] = pdf

if not st.session_state.major_program_data:
    st.info(
        "Click **Load Program Data** to fetch field-of-study information for your selected schools."
        if lang == "en"
        else "點擊「**載入科系資料**」以取得所選學校的科系資訊。"
    )
    st.stop()

# ── Combine & filter ──────────────────────────────────────────────────────────
all_dfs = list(st.session_state.major_program_data.values())
combined = pd.concat(all_dfs, ignore_index=True)

if selected_cip_2digit:
    combined = combined[combined["cip_2digit"] == selected_cip_2digit]
if selected_cred_level is not None:
    combined = combined[combined["cred_level"] == selected_cred_level]

combined = combined.dropna(subset=["median_earnings"])

st.markdown("---")

if combined.empty:
    st.warning(t("major_no_programs", lang))
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION A — Cross-School Comparison
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("📊 " + t("major_cross_title", lang))
st.caption(t("major_cross_desc", lang))

cred_label_col = "cred_label" if lang == "en" else "cred_label_zh"

# Grouped bar: earnings by school per field
top_fields = (
    combined.groupby("cip_title")["median_earnings"]
    .mean()
    .sort_values(ascending=False)
    .head(12)
    .index.tolist()
)
chart_data = combined[combined["cip_title"].isin(top_fields)].copy()
chart_data["short_field"] = chart_data["cip_title"].apply(
    lambda x: x[:30] + "..." if len(x) > 30 else x
)

if not chart_data.empty:
    fig_cross = px.bar(
        chart_data,
        x="median_earnings",
        y="short_field",
        color="school_name",
        barmode="group",
        orientation="h",
        facet_row=None,
        hover_data={
            cred_label_col: True,
            "median_earnings": ":$,.0f",
            "median_debt": ":$,.0f",
        },
        labels={
            "median_earnings": "Median Earnings ($)" if lang == "en" else "薪資中位數 ($)",
            "short_field": "",
            "school_name": "School" if lang == "en" else "學校",
        },
        height=max(350, len(top_fields) * 50),
        color_discrete_sequence=["#4D96FF", "#E8503A", "#6BCB77", "#FFD166", "#9B5DE5"],
    )
    fig_cross.update_xaxes(tickprefix="$", tickformat=",")
    fig_cross.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito", size=12),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        margin=dict(t=20),
    )
    st.plotly_chart(fig_cross, use_container_width=True)

# Earnings vs Debt scatter
st.markdown("#### " + t("chart_earn_debt_scatter", lang))
fig_scatter = px.scatter(
    combined,
    x="median_debt",
    y="median_earnings",
    color="school_name",
    symbol=cred_label_col,
    hover_name="cip_title",
    hover_data={
        "school_name": True,
        cred_label_col: True,
        "median_earnings": ":$,.0f",
        "median_debt": ":$,.0f",
        "prog_debt_ratio": ":.2f",
    },
    labels={
        "median_debt": "Median Debt ($)" if lang == "en" else "學貸中位數 ($)",
        "median_earnings": "Median Earnings ($)" if lang == "en" else "薪資中位數 ($)",
        "school_name": "School" if lang == "en" else "學校",
        cred_label_col: "Credential" if lang == "en" else "學位",
    },
    height=440,
    color_discrete_sequence=["#4D96FF", "#E8503A", "#6BCB77", "#FFD166", "#9B5DE5"],
)
fig_scatter.update_traces(marker=dict(size=12, opacity=0.8))
fig_scatter.update_xaxes(tickprefix="$", tickformat=",")
fig_scatter.update_yaxes(tickprefix="$", tickformat=",")
fig_scatter.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Nunito", size=12),
)
st.plotly_chart(fig_scatter, use_container_width=True)
st.caption(
    "Top-left = high earnings + low debt = best value. "
    "Data: College Scorecard Field of Study (U.S. Dept. of Education)"
    if lang == "en"
    else "左上角 = 高薪低貸 = 最佳 CP 值。資料來源：College Scorecard 科系資料（美國教育部）"
)

# Ranking table
st.markdown("#### " + ("Earnings Ranking by Program" if lang == "en" else "科系薪資排名"))
rank_cols = {
    "school_name": "School" if lang == "en" else "學校",
    "cip_title": "Field" if lang == "en" else "科系",
    cred_label_col: "Credential" if lang == "en" else "學位",
    "median_earnings": "Earnings" if lang == "en" else "薪資",
    "median_debt": "Debt" if lang == "en" else "學貸",
    "prog_debt_ratio": "Debt/Earn" if lang == "en" else "學貸/薪資",
}
rank_df = (
    combined[list(rank_cols.keys())]
    .sort_values("median_earnings", ascending=False)
    .reset_index(drop=True)
)
rank_df.index += 1
rank_df = rank_df.rename(columns=rank_cols)
earn_col = "Earnings" if lang == "en" else "薪資"
debt_col = "Debt" if lang == "en" else "學貸"
ratio_col = "Debt/Earn" if lang == "en" else "學貸/薪資"
rank_df[earn_col] = rank_df[earn_col].apply(fmt_usd)
rank_df[debt_col] = rank_df[debt_col].apply(
    lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
)
rank_df[ratio_col] = rank_df[ratio_col].apply(
    lambda x: f"{x:.2f}" if pd.notna(x) and x is not None else "N/A"
)
st.dataframe(rank_df, use_container_width=True, height=320)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION B — Graduate Premium Calculator
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🎓 " + t("major_premium_title", lang))
st.caption(t("major_premium_desc", lang))

# Let user pick a school and field of study
school_names_available = list(st.session_state.major_program_data.keys())
if not school_names_available:
    st.info(t("major_premium_no_data", lang))
    st.stop()

prem_school = st.selectbox(
    "Select a school / 選擇學校",
    school_names_available,
    key="prem_school_select",
)
school_pdf = st.session_state.major_program_data.get(prem_school, pd.DataFrame())

if school_pdf.empty:
    st.info(t("major_premium_no_data", lang))
    st.stop()

# Find fields with both Bachelor's (level 3) and Master's (level 6)
ug = school_pdf[school_pdf["cred_level"] == 3][["cip_title", "median_earnings", "median_debt"]].rename(
    columns={"median_earnings": "ug_earn", "median_debt": "ug_debt"}
)
ms = school_pdf[school_pdf["cred_level"] == 6][["cip_title", "median_earnings", "median_debt"]].rename(
    columns={"median_earnings": "ms_earn", "median_debt": "ms_debt"}
)
combined_prem = ug.merge(ms, on="cip_title").dropna(subset=["ug_earn", "ms_earn"])

if combined_prem.empty:
    st.info(
        f"No fields at {prem_school} have both Bachelor's and Master's earnings data."
        if lang == "en"
        else f"{prem_school} 目前沒有同時具備學士與碩士薪資資料的科系。"
    )
    st.stop()

field_options = combined_prem["cip_title"].tolist()
prem_field = st.selectbox(
    "Select a field of study / 選擇科系",
    field_options,
    key="prem_field_select",
)

prem_row = combined_prem[combined_prem["cip_title"] == prem_field].iloc[0]
ug_earn = prem_row["ug_earn"]
ms_earn = prem_row["ms_earn"]
ug_debt = prem_row.get("ug_debt") or 0
ms_debt = prem_row.get("ms_debt") or 0

# Grad school years input
ms_years = st.slider(
    "Years spent in Master's program / 碩士就讀年數",
    min_value=1, max_value=4, value=2, key="prem_ms_years",
)

# Opportunity cost = foregone bachelor's earnings while in grad school
opportunity_cost = ug_earn * ms_years
extra_debt = max(0, ms_debt - ug_debt)
extra_tuition = st.number_input(
    "Additional annual tuition for Master's (beyond undergrad net price) / 碩士每年額外學費",
    min_value=0,
    max_value=100000,
    value=int(extra_debt / ms_years) if ms_years > 0 else 20000,
    step=1000,
    key="prem_extra_tuition",
)
extra_cost = (extra_tuition * ms_years) + opportunity_cost
earn_premium = ms_earn - ug_earn

# Display results
st.markdown("---")
p1, p2, p3 = st.columns(3)
with p1:
    st.metric(
        t("major_premium_extra_cost", lang),
        fmt_usd(extra_cost),
        help=(
            f"Tuition: {fmt_usd(extra_tuition * ms_years)}  +  "
            f"Opportunity cost: {fmt_usd(opportunity_cost)}"
            if lang == "en"
            else f"學費：{fmt_usd(extra_tuition * ms_years)}  +  機會成本：{fmt_usd(opportunity_cost)}"
        ),
    )
with p2:
    st.metric(
        t("major_premium_earn_premium", lang),
        fmt_usd(earn_premium) if earn_premium else "N/A",
        delta=f"{'Master' if lang == 'en' else '碩士'} {fmt_usd(ms_earn)} vs {'Bachelor' if lang == 'en' else '學士'} {fmt_usd(ug_earn)}",
    )
with p3:
    if earn_premium and earn_premium > 0:
        payback = round(extra_cost / earn_premium, 1)
        animal = get_cp_animal(1 / payback * 5 if payback > 0 else None)
        st.metric(
            t("major_premium_payback", lang),
            f"{payback} {'yrs' if lang == 'en' else '年'}",
            help=(
                "Years of earnings premium needed to recover the extra cost"
                if lang == "en"
                else "需要幾年的薪資溢價才能回收額外成本"
            ),
        )
        if payback < 3:
            st.success(
                f"{animal['emoji']} Excellent ROI — Master's pays off in under 3 years!"
                if lang == "en"
                else f"{animal['emoji']} 超值！碩士學位不到 3 年即可回本！"
            )
        elif payback < 7:
            st.info(
                f"{animal['emoji']} Good ROI — pays off in {payback:.1f} years."
                if lang == "en"
                else f"{animal['emoji']} 不錯的 CP 值，約 {payback:.1f} 年回本。"
            )
        else:
            st.warning(
                f"{animal['emoji']} Long payback ({payback:.1f} yrs) — consider if it's worth it."
                if lang == "en"
                else f"{animal['emoji']} 回本年數較長（{payback:.1f} 年），請仔細評估是否值得。"
            )
    else:
        st.metric(t("major_premium_payback", lang), "N/A")
        if earn_premium is not None and earn_premium <= 0:
            st.error(
                "Master's earnings are not higher than Bachelor's in this field."
                if lang == "en"
                else "此科系碩士薪資未高於學士，建議重新評估。"
            )

# Bar chart comparing earnings
fig_prem = go.Figure()
creds_labels = (
    ["Bachelor's", "Master's"] if lang == "en" else ["學士", "碩士"]
)
fig_prem.add_trace(go.Bar(
    x=creds_labels,
    y=[ug_earn, ms_earn],
    marker_color=["#4D96FF", "#6BCB77"],
    text=[fmt_usd(ug_earn), fmt_usd(ms_earn)],
    textposition="outside",
))
fig_prem.update_yaxes(tickprefix="$", tickformat=",")
fig_prem.update_layout(
    title=(
        f"Earnings Comparison — {prem_field[:40]}"
        if lang == "en"
        else f"薪資比較 — {prem_field[:40]}"
    ),
    height=320,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Nunito", size=13),
    showlegend=False,
    margin=dict(t=50),
)
st.plotly_chart(fig_prem, use_container_width=True)
st.caption(
    "Earnings are 1-year post-completion medians from College Scorecard Field of Study data."
    if lang == "en"
    else "薪資為畢業 1 年後中位數，來源：College Scorecard 科系層級資料（美國教育部）。"
)
