"""
Page 1 — University Search
Search 6,000+ U.S. colleges and view key financial + academic metrics.
"""

import streamlit as st
import pandas as pd
from utils.translations import t, US_STATES
from utils.api import search_schools, results_to_df, fmt_usd, fmt_pct
from utils.calculations import enrich_df, score_label, debt_label

st.set_page_config(page_title="University Search", page_icon="🔍", layout="wide")

lang = st.session_state.get("lang", "en")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.caption(t("data_source", lang))

# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"🔍 {t('search_title', lang)}")
st.markdown(t("search_desc", lang))
st.markdown("---")

# ── Search & filter controls ──────────────────────────────────────────────────
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    query = st.text_input(
        t("school_name", lang),
        placeholder=t("search_placeholder", lang),
    )
with col2:
    state_filter = st.selectbox(t("filter_state", lang), US_STATES)
with col3:
    type_options_en = ["All", "Public", "Private Nonprofit", "Private For-Profit"]
    type_options_zh = ["全部", "公立", "私立非營利", "私立營利"]
    type_options = type_options_en if lang == "en" else type_options_zh
    type_filter = st.selectbox(t("filter_type", lang), type_options)

col4, col5 = st.columns([2, 1])
with col4:
    size_opts_en = ["Any size", "Small (< 2,000)", "Medium (2,000–15,000)", "Large (> 15,000)"]
    size_opts_zh = ["不限", "小型（< 2,000 人）", "中型（2,000–15,000 人）", "大型（> 15,000 人）"]
    size_opts = size_opts_en if lang == "en" else size_opts_zh
    size_filter = st.selectbox(t("filter_size", lang), size_opts)
with col5:
    per_page = st.selectbox("Results per page / 每頁筆數", [10, 25, 50], index=1)

# Map UI values to API params
size_map = {
    size_opts[0]: (0, 9_999_999),
    size_opts[1]: (0, 1_999),
    size_opts[2]: (2_000, 15_000),
    size_opts[3]: (15_001, 9_999_999),
}
min_size, max_size = size_map.get(size_filter, (0, 9_999_999))

ownership_map = {
    type_options[0]: 0,
    type_options[1]: 1,
    type_options[2]: 2,
    type_options[3]: 3,
}
ownership = ownership_map.get(type_filter, 0)

# Pagination
if "search_page" not in st.session_state:
    st.session_state.search_page = 0

if st.button(f"🔍 {t('search', lang)}", type="primary"):
    st.session_state.search_page = 0  # Reset page on new search

# ── Fetch results ─────────────────────────────────────────────────────────────
with st.spinner(t("loading", lang)):
    results, total = search_schools(
        name=query,
        state="" if state_filter == "All" else state_filter,
        ownership=ownership,
        min_size=min_size,
        max_size=max_size,
        per_page=per_page,
        page=st.session_state.search_page,
    )

if not results:
    if query or state_filter != "All" or type_filter != type_options[0]:
        st.warning(t("no_results", lang))
    else:
        st.info("Enter a school name or apply filters above to search." if lang == "en"
                else "請輸入學校名稱或選擇篩選條件開始搜尋。")
    st.stop()

df = results_to_df(results)
df = enrich_df(df)

# ── Results summary ───────────────────────────────────────────────────────────
st.markdown(f"**{total:,} {t('results_found', lang)}**  "
            f"(showing {st.session_state.search_page * per_page + 1}–"
            f"{min(st.session_state.search_page * per_page + per_page, total)})")

# ── Results table ─────────────────────────────────────────────────────────────
display_df = df[[
    "name", "state", "type_en" if lang == "en" else "type_zh",
    "tuition_out", "net_price", "earnings_10yr", "median_debt",
    "completion_rate", "admission_rate", "value_score",
]].copy()

display_df.columns = [
    t("school_name", lang),
    t("state", lang),
    t("type", lang),
    t("tuition_outstate", lang),
    t("net_price", lang),
    t("earnings_10yr", lang),
    t("median_debt", lang),
    t("completion_rate", lang),
    t("admission_rate", lang),
    t("value_score", lang),
]

# Format columns
for col in [t("tuition_outstate", lang), t("net_price", lang),
            t("earnings_10yr", lang), t("median_debt", lang)]:
    if col in display_df.columns:
        display_df[col] = display_df[col].apply(lambda x: fmt_usd(x))

for col in [t("completion_rate", lang), t("admission_rate", lang)]:
    if col in display_df.columns:
        display_df[col] = display_df[col].apply(lambda x: fmt_pct(x))

display_df[t("value_score", lang)] = display_df[t("value_score", lang)].apply(
    lambda x: f"{x:.1f}" if pd.notna(x) and x is not None else "N/A"
)

st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Pagination ────────────────────────────────────────────────────────────────
total_pages = (total // per_page) + (1 if total % per_page else 0)
p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
with p_col1:
    if st.session_state.search_page > 0:
        if st.button("← Previous"):
            st.session_state.search_page -= 1
            st.rerun()
with p_col2:
    st.markdown(
        f"<div style='text-align:center'>Page {st.session_state.search_page + 1} / {total_pages}</div>",
        unsafe_allow_html=True
    )
with p_col3:
    if (st.session_state.search_page + 1) * per_page < total:
        if st.button("Next →"):
            st.session_state.search_page += 1
            st.rerun()

st.markdown("---")

# ── School profile expander ───────────────────────────────────────────────────
st.subheader(t("school_profile", lang))
school_names = df["name"].dropna().tolist()
selected_name = st.selectbox(
    "Select a school for details / 選擇學校查看詳情",
    ["— select —"] + school_names,
)

if selected_name != "— select —":
    row = df[df["name"] == selected_name].iloc[0]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"### {row['name']}")
        st.markdown(f"**{row['city']}, {row['state']}**")
        inst_type = row["type_en"] if lang == "en" else row["type_zh"]
        st.markdown(f"*{inst_type}*")
        if pd.notna(row.get("url")) and row.get("url"):
            st.link_button(t("visit_website", lang), f"https://{row['url']}" if not str(row['url']).startswith("http") else row['url'])
        if pd.notna(row.get("npc_url")) and row.get("npc_url"):
            st.link_button(t("net_price_calc", lang), row["npc_url"])

    with c2:
        st.markdown("**Cost**" if lang == "en" else "**學費資訊**")
        st.metric(t("tuition_instate", lang), fmt_usd(row.get("tuition_in")))
        st.metric(t("tuition_outstate", lang), fmt_usd(row.get("tuition_out")))
        st.metric(t("net_price", lang), fmt_usd(row.get("net_price")))
        st.metric(t("median_debt", lang), fmt_usd(row.get("median_debt")))

    with c3:
        st.markdown("**Outcomes**" if lang == "en" else "**就業結果**")
        st.metric(t("earnings_6yr", lang), fmt_usd(row.get("earnings_6yr")))
        st.metric(t("earnings_10yr", lang), fmt_usd(row.get("earnings_10yr")))
        st.metric(t("completion_rate", lang), fmt_pct(row.get("completion_rate")))
        st.metric(t("admission_rate", lang), fmt_pct(row.get("admission_rate")))

    # ROI metrics
    st.markdown("---")
    roi_cols = st.columns(3)
    with roi_cols[0]:
        vs = row.get("value_score")
        label = score_label(vs, lang)
        st.metric(
            t("value_score", lang),
            f"{vs:.2f} ({label})" if vs else "N/A",
            help=t("value_score_help", lang),
        )
    with roi_cols[1]:
        dti = row.get("debt_to_income")
        st.metric(
            t("debt_to_income", lang),
            debt_label(dti, lang),
            help=t("debt_to_income_help", lang),
        )
    with roi_cols[2]:
        py = row.get("payback_years")
        label_py = f"{py:.1f} yrs" if py else "N/A"
        if lang == "zh":
            label_py = f"{py:.1f} 年" if py else "N/A"
        st.metric(
            "Payback Years / 回本年數",
            label_py,
            help="Years of post-grad earnings needed to cover 4-year tuition" if lang == "en"
                 else "幾年薪資可覆蓋四年學費",
        )

    # Aid summary
    st.markdown("---")
    aid_cols = st.columns(2)
    with aid_cols[0]:
        st.markdown(f"**{t('pell_rate', lang)}:** {fmt_pct(row.get('pell_rate'))}")
        st.markdown(f"**{t('loan_rate', lang)}:** {fmt_pct(row.get('loan_rate'))}")
    with aid_cols[1]:
        st.markdown(f"**{t('enrollment', lang)}:** {row.get('enrollment', 'N/A'):,}" if row.get('enrollment') else f"**{t('enrollment', lang)}:** N/A")
        st.markdown(f"**{t('sat_avg', lang)}:** {row.get('sat_avg', 'N/A')}")
