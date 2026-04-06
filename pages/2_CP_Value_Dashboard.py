"""
Page 2 — CP Value (ROI) Dashboard
Compare up to 5 colleges side-by-side on cost, earnings, and value score.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.translations import t
from utils.api import search_schools, results_to_df, fmt_usd, fmt_pct
from utils.calculations import enrich_df, score_label, debt_label

st.set_page_config(page_title="CP Value Dashboard", page_icon="📊", layout="wide")

lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.caption(t("data_source", lang))

st.title(f"📊 {t('cp_title', lang)}")
st.markdown(t("cp_desc", lang))

# ── How-to interpret ──────────────────────────────────────────────────────────
with st.expander(t("interpretation_title", lang)):
    st.markdown(t("interpretation_text", lang))

st.markdown("---")

# ── School comparison state ───────────────────────────────────────────────────
if "compare_schools" not in st.session_state:
    st.session_state.compare_schools = []   # list of school dicts (from results_to_df)

# ── Add school widget ─────────────────────────────────────────────────────────
st.subheader(t("add_school", lang))
add_col1, add_col2 = st.columns([4, 1])
with add_col1:
    add_query = st.text_input(
        t("search_to_add", lang),
        key="add_search",
        label_visibility="collapsed",
        placeholder=t("search_to_add", lang),
    )
with add_col2:
    do_search = st.button("Search / 搜尋", type="primary")

if add_query and (do_search or len(add_query) > 3):
    with st.spinner(t("loading", lang)):
        results, _ = search_schools(name=add_query, per_page=10)
    if results:
        candidate_df = results_to_df(results)
        candidate_df = enrich_df(candidate_df)
        candidate_names = candidate_df["name"].dropna().tolist()

        chosen = st.selectbox(
            "Select school / 選擇學校",
            ["— pick one —"] + candidate_names,
            key="add_select",
        )
        if chosen != "— pick one —":
            already_ids = [s["id"] for s in st.session_state.compare_schools]
            chosen_row = candidate_df[candidate_df["name"] == chosen].iloc[0]
            if len(st.session_state.compare_schools) >= 5:
                st.warning("Maximum 5 schools. Remove one first." if lang == "en"
                           else "最多比較 5 所學校，請先移除一所。")
            elif chosen_row["id"] in already_ids:
                st.info("Already added." if lang == "en" else "已加入比較清單。")
            else:
                if st.button(f"+ Add {chosen}" if lang == "en" else f"+ 加入 {chosen}"):
                    st.session_state.compare_schools.append(chosen_row.to_dict())
                    st.rerun()
    else:
        st.warning(t("no_results", lang))

# ── Display / remove current list ────────────────────────────────────────────
if st.session_state.compare_schools:
    st.markdown("**Schools in comparison / 比較清單：**")
    remove_cols = st.columns(len(st.session_state.compare_schools))
    for idx, school in enumerate(st.session_state.compare_schools):
        with remove_cols[idx]:
            st.markdown(f"**{school['name']}**  \n{school.get('state','')}")
            if st.button("✕ Remove" if lang == "en" else "✕ 移除", key=f"remove_{idx}"):
                st.session_state.compare_schools.pop(idx)
                st.rerun()

if st.button("🗑 Clear all / 清除全部"):
    st.session_state.compare_schools = []
    st.rerun()

st.markdown("---")

# ── Main comparison ───────────────────────────────────────────────────────────
if len(st.session_state.compare_schools) < 2:
    st.info(t("select_schools_prompt", lang))
    st.stop()

compare_df = pd.DataFrame(st.session_state.compare_schools)

# ── Summary metrics table ─────────────────────────────────────────────────────
st.subheader(t("cp_rank", lang))

summary = compare_df[[
    "name", "state",
    "net_price", "earnings_10yr", "median_debt",
    "completion_rate", "value_score", "debt_to_income", "payback_years",
]].copy()

# Sort by value_score descending
summary = summary.sort_values("value_score", ascending=False).reset_index(drop=True)
summary.insert(0, "Rank", range(1, len(summary) + 1))

# Format for display
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
        "name": "School", "state": "State",
        "net_price": "Avg Net Price", "earnings_10yr": "10-Yr Earnings",
        "median_debt": "Median Debt", "completion_rate": "Grad Rate",
        "value_score": "Value Score ↑", "debt_to_income": "Debt/Income ↓",
        "payback_years": "Payback",
    },
    "zh": {
        "name": "學校", "state": "州",
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

if not chart_df.empty:
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
                t("annual_net_price", lang): "#E07070",
                t("earnings_label", lang): "#5AB5A0",
            },
            labels={"Amount": "USD ($)", "School": ""},
        )
        fig1.update_layout(
            legend_title="",
            xaxis_tickangle=-20,
            height=380,
        )
        st.plotly_chart(fig1, use_container_width=True)

    with ch2:
        st.subheader(t("chart_value_score", lang))
        sorted_df = chart_df.dropna(subset=["value_score"]).sort_values("value_score")
        fig2 = px.bar(
            sorted_df,
            x="value_score", y="name",
            orientation="h",
            color="value_score",
            color_continuous_scale="RdYlGn",
            labels={"value_score": t("value_score", lang), "name": ""},
            text="value_score",
        )
        fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig2.update_layout(coloraxis_showscale=False, height=380)
        st.plotly_chart(fig2, use_container_width=True)

    # Debt burden chart
    st.markdown("---")
    st.subheader(t("chart_debt_burden", lang))
    debt_df = chart_df.dropna(subset=["debt_to_income"]).sort_values("debt_to_income")

    fig3 = px.bar(
        debt_df,
        x="name", y="debt_to_income",
        color="debt_to_income",
        color_continuous_scale="RdYlGn_r",
        labels={"debt_to_income": "Debt / Earnings Ratio", "name": ""},
        text="debt_to_income",
    )
    fig3.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig3.add_hline(y=1.0, line_dash="dash", line_color="orange",
                   annotation_text="1.0 — caution threshold" if lang == "en" else "1.0 —警戒線")
    fig3.update_layout(coloraxis_showscale=False, height=360)
    st.plotly_chart(fig3, use_container_width=True)

    # Radar / Spider chart for holistic comparison
    if len(chart_df) >= 2:
        st.markdown("---")
        st.subheader("Holistic Comparison / 全面比較" if lang == "en" else "全面比較")

        # Normalize metrics 0-1 for radar
        radar_df = chart_df[["name", "value_score", "completion_rate", "admission_rate",
                              "earnings_10yr", "median_debt"]].copy()
        radar_df["debt_score"] = 1 - (radar_df["median_debt"] / radar_df["median_debt"].max())
        radar_df["earn_score"] = radar_df["earnings_10yr"] / radar_df["earnings_10yr"].max()
        radar_df["completion_n"] = radar_df["completion_rate"].fillna(0)
        radar_df["vs_n"] = radar_df["value_score"] / radar_df["value_score"].max()

        categories = (
            ["Value Score", "Grad Rate", "Low Debt", "Earnings", "Selectivity"]
            if lang == "en"
            else ["CP值", "畢業率", "低負債", "薪資", "篩選度"]
        )

        fig4 = go.Figure()
        for _, row in radar_df.iterrows():
            sel = 1 - (row.get("admission_rate") or 0.5)
            values = [
                row.get("vs_n") or 0,
                row.get("completion_n") or 0,
                row.get("debt_score") or 0,
                row.get("earn_score") or 0,
                sel,
            ]
            fig4.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=row["name"],
                opacity=0.6,
            ))
        fig4.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            height=450,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        )
        st.plotly_chart(fig4, use_container_width=True)
        st.caption("All axes normalized to 0–1. Higher = better on all dimensions." if lang == "en"
                   else "所有軸已標準化為 0–1，數值越高越好。")
