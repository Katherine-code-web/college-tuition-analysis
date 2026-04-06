"""
Page 4 — Spending Trends
Integrates existing IPEDS analysis: how colleges allocate tuition revenue.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from utils.translations import t

st.set_page_config(page_title="Spending Trends", page_icon="📈", layout="wide")

lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.caption(t("data_source", lang))

st.title(f"📈 {t('trend_title', lang)}")
st.markdown(t("trend_desc", lang))
st.markdown("---")

# ── Key findings (static, always shown) ──────────────────────────────────────
st.subheader(t("trend_key_findings", lang))
f1, f2, f3, f4 = st.columns(4)
with f1:
    st.error(f"📉 {t('trend_finding1', lang)}")
with f2:
    st.warning(f"📈 {t('trend_finding2', lang)}")
with f3:
    st.info(f"🏛 {t('trend_finding3', lang)}")
with f4:
    st.error(f"🏛 {t('trend_finding4', lang)}")

st.markdown("---")

# ── Try to load IPEDS data ────────────────────────────────────────────────────
DATA_PATH = "data/panel_2018_2023.csv"
CORRECTED_PATH = "outputs/panel_2018_2023_corrected.csv"

df = None
if os.path.exists(CORRECTED_PATH):
    df = pd.read_csv(CORRECTED_PATH)
    st.success("Using corrected dataset." if lang == "en" else "使用已修正資料集。")
elif os.path.exists(DATA_PATH):
    df = pd.read_csv(DATA_PATH)
    st.info("Using raw dataset. Run `analyze_spending_trends.py` for corrected version."
            if lang == "en"
            else "使用原始資料集。執行 `analyze_spending_trends.py` 可取得修正版本。")

if df is None:
    # Show static charts from known findings
    st.warning(t("data_not_loaded", lang))

    st.subheader(t("chart_spending_share", lang))
    # Static 2023 composition chart based on known IPEDS findings
    categories_en = ["Instruction", "Administration", "Student Services", "Operations", "Research", "Other"]
    categories_zh = ["教學", "行政", "學生服務", "營運", "研究", "其他"]
    values_pub = [48.7, 13.5, 11.3, 20.0, 3.0, 3.5]
    values_priv = [42.3, 25.5, 18.3, 10.0, 2.0, 1.9]

    cats = categories_en if lang == "en" else categories_zh
    static_df = pd.DataFrame({
        "Category": cats * 2,
        "Institution Type": (
            ["Public" if lang == "en" else "公立"] * 6 +
            ["Private" if lang == "en" else "私立"] * 6
        ),
        "Percentage": values_pub + values_priv,
    })
    fig = px.bar(
        static_df, x="Category", y="Percentage",
        color="Institution Type",
        barmode="group",
        labels={"Percentage": "% of Total Budget", "Category": ""},
        color_discrete_map={
            "Public": "#2E86AB", "Private": "#A23B72",
            "公立": "#2E86AB", "私立": "#A23B72",
        },
    )
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Chart based on published IPEDS 2023 findings. Upload data for year-by-year trend."
        if lang == "en"
        else "圖表基於已發表的 IPEDS 2023 研究發現。上傳資料後可查看逐年趨勢。"
    )
    st.stop()

# ── Full interactive analysis (data loaded) ───────────────────────────────────
years = sorted(df["year"].unique())

# Filter controls
col1, col2 = st.columns(2)
with col1:
    selected_years = st.select_slider(
        "Year range / 年份範圍",
        options=years,
        value=(min(years), max(years)),
    )
with col2:
    type_opts = (["All", "Public", "Private"] if lang == "en"
                 else ["全部", "Public", "Private"])
    type_filter = st.selectbox("Institution type / 學校類型", type_opts)

fdf = df[(df["year"] >= selected_years[0]) & (df["year"] <= selected_years[1])].copy()
if type_filter not in ("All", "全部"):
    fdf = fdf[fdf["type"] == type_filter]

st.markdown("---")

# ── Chart 1: Spending share trends ───────────────────────────────────────────
st.subheader(t("chart_spending_share", lang))
share_trend = fdf.groupby("year")[["admin_pct", "instruction_pct", "research_pct"]].mean().reset_index()
share_trend["admin_pct"] *= 100
share_trend["instruction_pct"] *= 100
share_trend["research_pct"] *= 100

fig1 = go.Figure()
labels = (
    {"admin_pct": "Administrative", "instruction_pct": "Instructional", "research_pct": "Research"}
    if lang == "en"
    else {"admin_pct": "行政", "instruction_pct": "教學", "research_pct": "研究"}
)
colors = {"admin_pct": "#E07070", "instruction_pct": "#5AB5A0", "research_pct": "#7DA8D4"}
for col, label in labels.items():
    fig1.add_trace(go.Scatter(
        x=share_trend["year"], y=share_trend[col],
        name=label, mode="lines+markers",
        line=dict(width=2.5, color=colors[col]),
        marker=dict(size=8),
    ))
fig1.update_layout(
    xaxis_title="Year", yaxis_title="% of Total Budget",
    height=380, legend=dict(orientation="h", yanchor="bottom", y=-0.3),
)
st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2: Public vs Private admin spending ─────────────────────────────────
st.subheader(t("chart_admin_vs_inst", lang))

pub_priv = df[(df["year"] >= selected_years[0]) & (df["year"] <= selected_years[1])].copy()
pub_priv["admin_pct"] *= 100
pub_priv["instruction_pct"] *= 100

grouped = pub_priv.groupby(["year", "type"])[["admin_pct", "instruction_pct"]].mean().reset_index()

fig2_col1, fig2_col2 = st.columns(2)
with fig2_col1:
    fig2a = px.line(
        grouped, x="year", y="admin_pct", color="type",
        labels={"admin_pct": "Admin % of Budget", "year": "Year", "type": ""},
        title="Administrative Spending %" if lang == "en" else "行政支出佔比",
        color_discrete_map={"Public": "#2E86AB", "Private": "#A23B72"},
        markers=True,
    )
    fig2a.update_layout(height=340)
    st.plotly_chart(fig2a, use_container_width=True)

with fig2_col2:
    fig2b = px.line(
        grouped, x="year", y="instruction_pct", color="type",
        labels={"instruction_pct": "Instruction % of Budget", "year": "Year", "type": ""},
        title="Instructional Spending %" if lang == "en" else "教學支出佔比",
        color_discrete_map={"Public": "#2E86AB", "Private": "#A23B72"},
        markers=True,
    )
    fig2b.update_layout(height=340)
    st.plotly_chart(fig2b, use_container_width=True)

# ── Chart 3: Real per-FTE spending (if corrected columns exist) ───────────────
if "admin_per_fte_real" in fdf.columns:
    st.markdown("---")
    st.subheader(
        "Real Per-Student Spending Trends (2018 dollars)" if lang == "en"
        else "實質每生支出趨勢（2018年美元）"
    )

    real_trend = fdf.groupby(["year", "type"])[
        ["admin_per_fte_real", "instruction_per_fte_real"]
    ].median().reset_index()

    r1, r2 = st.columns(2)
    with r1:
        fig3a = px.line(
            real_trend, x="year", y="admin_per_fte_real", color="type",
            labels={"admin_per_fte_real": "$ per FTE (2018$)", "year": "Year", "type": ""},
            title="Real Admin per FTE" if lang == "en" else "實質行政支出 / 生",
            color_discrete_map={"Public": "#2E86AB", "Private": "#A23B72"},
            markers=True,
        )
        fig3a.update_layout(height=340)
        st.plotly_chart(fig3a, use_container_width=True)

    with r2:
        fig3b = px.line(
            real_trend, x="year", y="instruction_per_fte_real", color="type",
            labels={"instruction_per_fte_real": "$ per FTE (2018$)", "year": "Year", "type": ""},
            title="Real Instruction per FTE" if lang == "en" else "實質教學支出 / 生",
            color_discrete_map={"Public": "#2E86AB", "Private": "#A23B72"},
            markers=True,
        )
        fig3b.update_layout(height=340)
        st.plotly_chart(fig3b, use_container_width=True)

# ── State-level drilldown ─────────────────────────────────────────────────────
st.markdown("---")
st.subheader("State-Level Drilldown" if lang == "en" else "州別深入分析")

if "STABBR" in fdf.columns:
    latest = fdf[fdf["year"] == fdf["year"].max()].copy()
    latest["admin_pct_disp"] = latest["admin_pct"] * 100
    latest["instruction_pct_disp"] = latest["instruction_pct"] * 100

    state_agg = latest.groupby("STABBR").agg(
        admin_pct=("admin_pct_disp", "mean"),
        instruction_pct=("instruction_pct_disp", "mean"),
        n=("UNITID", "count"),
    ).reset_index().sort_values("admin_pct", ascending=False)

    top_n = st.slider(
        "Top N states by admin spending" if lang == "en" else "依行政支出排名前 N 州",
        5, 20, 10,
    )
    display_states = state_agg.head(top_n)

    fig_state = px.bar(
        display_states,
        x="STABBR", y=["admin_pct", "instruction_pct"],
        barmode="group",
        labels={
            "STABBR": "State", "value": "% of Budget",
            "admin_pct": "Admin %" if lang == "en" else "行政%",
            "instruction_pct": "Instruction %" if lang == "en" else "教學%",
        },
        color_discrete_map={
            "admin_pct": "#E07070",
            "instruction_pct": "#5AB5A0",
        },
        title=f"Top {top_n} States by Admin Spending ({fdf['year'].max()})"
              if lang == "en"
              else f"行政支出最高的 {top_n} 個州（{fdf['year'].max()}年）",
    )
    fig_state.update_layout(height=420)
    st.plotly_chart(fig_state, use_container_width=True)

# ── Data download ─────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("Download filtered data / 下載篩選後資料"):
    st.dataframe(fdf.head(200), use_container_width=True)
    csv = fdf.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        csv,
        file_name="ipeds_filtered.csv",
        mime="text/csv",
    )
