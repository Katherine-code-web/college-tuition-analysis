"""
Page 2 — CP Value (ROI) Dashboard
Compare up to 5 colleges side-by-side on cost, earnings, and value score.
"""

import streamlit as st
from utils.theme import get_theme_css
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.translations import t
from utils.api import search_schools, results_to_df, fmt_usd, fmt_pct, get_school_programs
from utils.calculations import (
    enrich_df, score_label, debt_label, get_cp_animal,
    programs_to_df, CIP_CATEGORIES, CIP_CATEGORIES_ZH,
)

st.set_page_config(page_title="CP Value Dashboard", page_icon="📊", layout="wide")
st.markdown(get_theme_css(), unsafe_allow_html=True)

lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.caption(t("data_source", lang))

st.title(f"📊 {t('cp_title', lang)}")
st.markdown(t("cp_desc", lang))
st.markdown("---")

# ── Session state init ────────────────────────────────────────────────────────
if "compare_schools" not in st.session_state:
    st.session_state.compare_schools = []   # list of school dicts
if "cp_search_results" not in st.session_state:
    st.session_state.cp_search_results = []  # cached search results
if "cp_search_query" not in st.session_state:
    st.session_state.cp_search_query = ""

# ── Add school section ────────────────────────────────────────────────────────
st.subheader(t("add_school", lang))

add_query = st.text_input(
    "search",
    key="add_search_input",
    label_visibility="collapsed",
    placeholder=t("search_to_add", lang),
)
do_search = st.button("🔍 " + t("search", lang), type="primary")

# Run search only when button is clicked
if do_search and add_query:
    with st.spinner(t("loading", lang)):
        results, _ = search_schools(name=add_query, per_page=10)
    if results:
        df_results = results_to_df(results)
        df_results = enrich_df(df_results)
        st.session_state.cp_search_results = df_results.to_dict("records")
        st.session_state.cp_search_query = add_query
    else:
        st.session_state.cp_search_results = []
        st.warning(t("no_results", lang))

# Show search results as buttons (avoids selectbox state loss on rerun)
if st.session_state.cp_search_results:
    st.markdown(
        f"**{'Results for' if lang == 'en' else '搜尋結果：'} \"{st.session_state.cp_search_query}\"**"
    )
    already_ids = {s["id"] for s in st.session_state.compare_schools}

    result_cols = st.columns(2)
    for i, school in enumerate(st.session_state.cp_search_results[:8]):
        with result_cols[i % 2]:
            is_added = school["id"] in already_ids
            is_full = len(st.session_state.compare_schools) >= 5

            vs = school.get("value_score")
            vs_str = f"  ·  CP: {vs:.1f}" if vs else ""
            np_str = f"  ·  {fmt_usd(school.get('net_price'))}/yr" if school.get("net_price") else ""

            btn_label = (
                f"✓ Added" if is_added
                else f"+ {school['name']}"
            )
            btn_help = f"{school.get('city','')}, {school.get('state','')}{np_str}{vs_str}"

            if st.button(
                btn_label,
                key=f"add_btn_{school['id']}",
                disabled=is_added or is_full,
                use_container_width=True,
                help=btn_help,
            ):
                st.session_state.compare_schools.append(school)
                st.rerun()

    if len(st.session_state.compare_schools) >= 5:
        st.warning(
            "Maximum 5 schools reached. Remove one to add more."
            if lang == "en" else "最多比較 5 所學校，請先移除一所。"
        )

# ── Current comparison list ───────────────────────────────────────────────────
st.markdown("---")

if not st.session_state.compare_schools:
    st.info(
        "Search and add at least 2 schools above to start comparing."
        if lang == "en" else "請搜尋並加入至少 2 所學校開始比較。"
    )
    st.stop()

# Show added schools with remove buttons
st.markdown("**" + ("Comparing / 比較中：" if lang == "en" else "比較中：") + "**")
tag_cols = st.columns(min(len(st.session_state.compare_schools), 5))
for idx, school in enumerate(st.session_state.compare_schools):
    with tag_cols[idx]:
        animal = get_cp_animal(school.get("value_score"))
        st.markdown(f"""
        <div style="background:{animal['bg']};border:2px solid #1A1A1A;border-radius:10px;
                    padding:8px 10px;text-align:center;">
            <div style="font-size:1.6rem;">{animal['emoji']}</div>
            <div style="font-family:'Fredoka One',cursive;font-size:0.85rem;margin-top:2px;">{school['name']}</div>
            <div style="font-size:0.72rem;color:#555;">{school.get('state','')}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("✕", key=f"remove_{idx}_{school['id']}", use_container_width=True):
            st.session_state.compare_schools.pop(idx)
            st.rerun()

c1, c2 = st.columns([1, 5])
with c1:
    if st.button("🗑 " + ("Clear all" if lang == "en" else "清除全部"), use_container_width=True):
        st.session_state.compare_schools = []
        st.session_state.cp_search_results = []
        st.rerun()

st.markdown("---")

if len(st.session_state.compare_schools) < 2:
    st.info(t("select_schools_prompt", lang))
    st.stop()

# ── Build comparison dataframe ────────────────────────────────────────────────
compare_df = pd.DataFrame(st.session_state.compare_schools)

# ── Summary table ─────────────────────────────────────────────────────────────
st.subheader(t("cp_rank", lang))

summary = compare_df[[
    "name", "state",
    "net_price", "earnings_10yr", "median_debt",
    "completion_rate", "value_score", "debt_to_income", "payback_years",
]].copy()

# Add mascot emoji based on value_score
summary["mascot"] = summary["value_score"].map(lambda v: get_cp_animal(v)["emoji"])

summary = summary.sort_values("value_score", ascending=False).reset_index(drop=True)
summary.insert(0, "Rank", ["🥇","🥈","🥉","4th","5th"][:len(summary)])

summary["net_price"] = summary["net_price"].apply(fmt_usd)
summary["earnings_10yr"] = summary["earnings_10yr"].apply(fmt_usd)
summary["median_debt"] = summary["median_debt"].apply(fmt_usd)
summary["completion_rate"] = summary["completion_rate"].apply(fmt_pct)
summary["value_score"] = summary["value_score"].apply(
    lambda x: f"{x:.2f}" if pd.notna(x) and x is not None else "N/A"
)
summary["debt_to_income"] = summary["debt_to_income"].apply(
    lambda x: f"{x:.2f}" if pd.notna(x) and x is not None else "N/A"
)
summary["payback_years"] = summary["payback_years"].apply(
    lambda x: f"{x:.1f} {'yrs' if lang == 'en' else '年'}" if pd.notna(x) and x is not None else "N/A"
)

col_labels = {
    "en": {
        "name": "School", "state": "State", "mascot": "Animal",
        "net_price": "Net Price/yr", "earnings_10yr": "10-Yr Earnings",
        "median_debt": "Median Debt", "completion_rate": "Grad Rate",
        "value_score": "CP Score ↑", "debt_to_income": "Debt/Income ↓",
        "payback_years": "Payback",
    },
    "zh": {
        "name": "學校", "state": "州", "mascot": "動物",
        "net_price": "實際年學費", "earnings_10yr": "10年後薪資",
        "median_debt": "中位學貸", "completion_rate": "畢業率",
        "value_score": "CP值 ↑", "debt_to_income": "負債比 ↓",
        "payback_years": "回本年數",
    },
}
summary.rename(columns=col_labels.get(lang, col_labels["en"]), inplace=True)
st.dataframe(summary, use_container_width=True, hide_index=True)

# ── Charts ────────────────────────────────────────────────────────────────────
chart_df = pd.DataFrame(st.session_state.compare_schools).copy()
chart_df = chart_df.dropna(subset=["net_price", "earnings_10yr"])

if chart_df.empty:
    st.warning("Not enough data to render charts." if lang == "en" else "資料不足，無法顯示圖表。")
    st.stop()

st.markdown("---")
ch1, ch2 = st.columns(2)

with ch1:
    st.subheader(t("chart_tuition_vs_earn", lang))
    bar_data = pd.DataFrame({
        "School": chart_df["name"].tolist() * 2,
        "Category": (
            [t("annual_net_price", lang)] * len(chart_df) +
            [t("earnings_label", lang)] * len(chart_df)
        ),
        "Amount": chart_df["net_price"].tolist() + chart_df["earnings_10yr"].tolist(),
    })
    fig1 = px.bar(
        bar_data, x="School", y="Amount", color="Category",
        barmode="group",
        color_discrete_map={
            t("annual_net_price", lang): "#E8503A",
            t("earnings_label", lang): "#6BCB77",
        },
        labels={"Amount": "USD ($)", "School": ""},
    )
    fig1.update_layout(
        legend_title="", xaxis_tickangle=-20, height=380,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito", size=13),
    )
    fig1.update_yaxes(tickprefix="$", tickformat=",")
    st.plotly_chart(fig1, use_container_width=True)

with ch2:
    st.subheader(t("chart_value_score", lang))
    sorted_df = chart_df.dropna(subset=["value_score"]).sort_values("value_score")
    fig2 = px.bar(
        sorted_df, x="value_score", y="name",
        orientation="h",
        color="value_score",
        color_continuous_scale=["#E8503A", "#FFD166", "#6BCB77"],
        labels={"value_score": t("value_score", lang), "name": ""},
        text="value_score",
    )
    fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig2.update_layout(
        coloraxis_showscale=False, height=380,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito", size=13),
    )
    st.plotly_chart(fig2, use_container_width=True)

# Debt burden chart
st.markdown("---")
st.subheader(t("chart_debt_burden", lang))
debt_df = chart_df.dropna(subset=["debt_to_income"]).sort_values("debt_to_income")

if not debt_df.empty:
    fig3 = px.bar(
        debt_df, x="name", y="debt_to_income",
        color="debt_to_income",
        color_continuous_scale=["#6BCB77", "#FFD166", "#E8503A"],
        labels={"debt_to_income": "Debt / Earnings Ratio", "name": ""},
        text="debt_to_income",
    )
    fig3.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig3.add_hline(
        y=1.0, line_dash="dash", line_color="#FF8C42", line_width=2,
        annotation_text="1.0 — caution" if lang == "en" else "1.0 — 警戒線",
    )
    fig3.update_layout(
        coloraxis_showscale=False, height=360,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito", size=13),
    )
    st.plotly_chart(fig3, use_container_width=True)

# Radar chart
if len(chart_df) >= 2:
    st.markdown("---")
    st.subheader("Holistic Comparison" if lang == "en" else "全面雷達比較")

    radar_df = chart_df[["name","value_score","completion_rate",
                          "admission_rate","earnings_10yr","median_debt"]].copy()

    max_earn = radar_df["earnings_10yr"].max() or 1
    max_debt = radar_df["median_debt"].max() or 1
    max_vs   = radar_df["value_score"].max() or 1

    radar_df["earn_n"]   = radar_df["earnings_10yr"] / max_earn
    radar_df["debt_n"]   = 1 - (radar_df["median_debt"].fillna(max_debt) / max_debt)
    radar_df["comp_n"]   = radar_df["completion_rate"].fillna(0)
    radar_df["vs_n"]     = radar_df["value_score"].fillna(0) / max_vs
    radar_df["sel_n"]    = 1 - (radar_df["admission_rate"].fillna(0.5))

    categories = (
        ["CP Value", "Grad Rate", "Low Debt", "Earnings", "Selectivity"]
        if lang == "en"
        else ["CP值", "畢業率", "低負債", "薪資", "入學難度"]
    )
    colors = ["#4D96FF","#E8503A","#6BCB77","#FFD166","#9B5DE5"]

    fig4 = go.Figure()
    for i, (_, row) in enumerate(radar_df.iterrows()):
        vals = [row["vs_n"], row["comp_n"], row["debt_n"], row["earn_n"], row["sel_n"]]
        fig4.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            fill="toself",
            name=row["name"],
            line=dict(color=colors[i % len(colors)], width=2),
            opacity=0.55,
        ))
    fig4.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,1], tickfont=dict(size=10)),
            bgcolor="rgba(255,255,255,0.8)",
        ),
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito", size=13),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    )
    st.plotly_chart(fig4, use_container_width=True)
    st.caption(
        "All axes normalized 0–1. Higher = better on all dimensions."
        if lang == "en" else "所有軸已標準化為 0–1，數值越高越好。"
    )

# ── Field of Study section ────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📚 " + t("filter_field_of_study", lang))
st.caption(
    "Select a field of study to compare the same program across your selected schools."
    if lang == "en"
    else "選擇一個科系領域，跨校比較該科系的薪資與學貸資料。"
)

# CIP category selector
cip_cat_labels = CIP_CATEGORIES if lang == "en" else CIP_CATEGORIES_ZH
cip_options = {
    ("All Fields" if lang == "en" else "全部科系"): None,
    **{f"{k} — {v}": k for k, v in cip_cat_labels.items()},
}
selected_cip_label = st.selectbox(
    t("major_filter_field", lang),
    list(cip_options.keys()),
    key="cp_dash_cip_select",
)
selected_cip_2digit = cip_options[selected_cip_label]

# Credential level selector
from utils.calculations import CRED_LEVEL_MAP, CRED_LEVEL_MAP_ZH
cred_map = CRED_LEVEL_MAP if lang == "en" else CRED_LEVEL_MAP_ZH
cred_filter_options = {
    ("All Levels" if lang == "en" else "全部層級"): None,
    **{v: k for k, v in cred_map.items()},
}
selected_cred_label = st.selectbox(
    t("major_filter_cred", lang),
    list(cred_filter_options.keys()),
    key="cp_dash_cred_select",
)
selected_cred_level = cred_filter_options[selected_cred_label]

# Fetch & aggregate program data for all compared schools
if st.button(
    "🔬 " + ("Load Program Data" if lang == "en" else "載入科系資料"),
    key="cp_load_programs",
):
    st.session_state.cp_program_data = {}
    with st.spinner(t("programs_loading", lang)):
        for school in st.session_state.compare_schools:
            sid = school.get("id")
            if sid:
                raw = get_school_programs(int(sid))
                if raw:
                    pdf = programs_to_df(
                        raw,
                        school_net_price=school.get("net_price"),
                        school_completion_rate=school.get("completion_rate"),
                    )
                    pdf["school_name"] = school["name"]
                    st.session_state.cp_program_data[school["name"]] = pdf

if "cp_program_data" in st.session_state and st.session_state.cp_program_data:
    all_prog_dfs = []
    for sname, pdf in st.session_state.cp_program_data.items():
        all_prog_dfs.append(pdf)

    if all_prog_dfs:
        combined = pd.concat(all_prog_dfs, ignore_index=True)

        # Apply CIP and credential filters
        if selected_cip_2digit:
            combined = combined[combined["cip_2digit"] == selected_cip_2digit]
        if selected_cred_level is not None:
            combined = combined[combined["cred_level"] == selected_cred_level]

        combined = combined.dropna(subset=["median_earnings"])

        if combined.empty:
            st.info(t("major_no_programs", lang))
        else:
            st.markdown("#### " + t("chart_earn_debt_scatter", lang))
            cred_label_col = "cred_label" if lang == "en" else "cred_label_zh"
            fig_scatter = px.scatter(
                combined,
                x="median_debt",
                y="median_earnings",
                color=cred_label_col,
                symbol="school_name",
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
                    cred_label_col: "Credential" if lang == "en" else "學位",
                    "school_name": "School" if lang == "en" else "學校",
                },
                height=460,
            )
            fig_scatter.update_traces(marker=dict(size=11, opacity=0.8))
            fig_scatter.update_xaxes(tickprefix="$", tickformat=",")
            fig_scatter.update_yaxes(tickprefix="$", tickformat=",")
            fig_scatter.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Nunito", size=12),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
            st.caption(
                "Each point = one program at one school. "
                "Top-left = high earnings + low debt = best value."
                if lang == "en"
                else "每個點 = 一所學校的一個科系。左上角 = 高薪低貸 = 最佳 CP 值。"
            )

            # Program ranking table
            st.markdown("#### " + ("Program Rankings" if lang == "en" else "科系 CP 值排名"))
            rank_df = combined[[
                "school_name", "cip_title", cred_label_col,
                "median_earnings", "median_debt", "prog_debt_ratio",
            ]].sort_values("median_earnings", ascending=False).reset_index(drop=True)
            rank_df.index = rank_df.index + 1
            rank_df.columns = [
                "School" if lang == "en" else "學校",
                "Field" if lang == "en" else "科系",
                "Credential" if lang == "en" else "學位",
                "Earnings" if lang == "en" else "薪資",
                "Debt" if lang == "en" else "學貸",
                "Debt/Earn" if lang == "en" else "學貸/薪資",
            ]
            rank_df["Earnings" if lang == "en" else "薪資"] = (
                rank_df["Earnings" if lang == "en" else "薪資"].apply(fmt_usd)
            )
            rank_df["Debt" if lang == "en" else "學貸"] = (
                rank_df["Debt" if lang == "en" else "學貸"].apply(
                    lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
                )
            )
            rank_df["Debt/Earn" if lang == "en" else "學貸/薪資"] = (
                rank_df["Debt/Earn" if lang == "en" else "學貸/薪資"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) and x is not None else "N/A"
                )
            )
            st.dataframe(rank_df, use_container_width=True, height=320)
else:
    st.info(
        "Click **Load Program Data** above after adding schools to see field-of-study comparisons."
        if lang == "en"
        else "新增學校後點擊「**載入科系資料**」以查看科系層級比較。"
    )
