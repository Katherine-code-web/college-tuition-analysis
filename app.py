"""
U.S. College Value & Scholarship Platform
Home page — entry point for Streamlit multipage app
"""

import streamlit as st
from utils.translations import t, T

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="U.S. College ROI Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Language selector (persisted in session state) ────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "en"

with st.sidebar:
    lang_choice = st.selectbox(
        "🌐 Language / 語言",
        ["English", "中文"],
        index=0 if st.session_state.lang == "en" else 1,
    )
    st.session_state.lang = "en" if lang_choice == "English" else "zh"
    lang = st.session_state.lang

    st.markdown("---")
    st.markdown("**Navigate / 導覽**")
    st.markdown(
        "Use the pages below 👇  \n"
        "使用下方頁面導覽 👇"
        if lang == "en"
        else "使用下方頁面導覽 👇"
    )
    st.markdown("---")
    st.caption(t("data_source", lang))

lang = st.session_state.lang

# ── Hero ──────────────────────────────────────────────────────────────────────
st.title(f"🎓 {t('app_title', lang)}")
st.markdown(f"#### {t('app_subtitle', lang)}")
st.markdown("---")

# ── Features grid ─────────────────────────────────────────────────────────────
st.subheader(t("home_features", lang))

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info(f"🔍 **{t('feat_search', lang)}**")
with col2:
    st.success(f"📊 **{t('feat_roi', lang)}**")
with col3:
    st.warning(f"🎓 **{t('feat_aid', lang)}**")
with col4:
    st.error(f"📈 **{t('feat_trend', lang)}**")

st.markdown("---")

# ── How CP Value works ────────────────────────────────────────────────────────
if lang == "en":
    st.subheader("How We Calculate CP Value (ROI Score)")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Value Score formula", "10-yr Earnings ÷ Net Price")
        st.caption("Higher = more earning power per tuition dollar paid")
    with col_b:
        st.metric("Debt-to-Income formula", "Median Debt ÷ 10-yr Earnings")
        st.caption("Lower = more manageable loan burden after graduation")
    with col_c:
        st.metric("Payback Years formula", "(Net Price × 4) ÷ 10-yr Earnings")
        st.caption("How many years of post-grad income covers your total tuition")
else:
    st.subheader("CP 值計算方式")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("CP 值分數公式", "10年後薪資 ÷ 實際年學費")
        st.caption("分數越高，每一塊學費買到的薪資潛力越大")
    with col_b:
        st.metric("負債收入比公式", "中位學貸 ÷ 10年後薪資")
        st.caption("比率越低，畢業後的還款壓力越小")
    with col_c:
        st.metric("回本年數公式", "（實際年學費 × 4）÷ 10年後薪資")
        st.caption("幾年薪資可以還清四年學費")

st.markdown("---")

# ── Quick explainer ───────────────────────────────────────────────────────────
if lang == "en":
    with st.expander("What is 'Net Price'? Why not just list tuition?"):
        st.markdown(
            """
            **Net Price** is the average amount students actually pay after grants and scholarships —
            it's a far better measure of real cost than the sticker tuition price.

            For example, a school may list $60,000/year tuition but the average student
            only pays $25,000 after financial aid. We use net price wherever possible.

            > Source: College Scorecard reports net price for first-time, full-time undergraduates
            receiving Title IV federal financial aid.
            """
        )
    with st.expander("What does '10-year earnings' mean?"):
        st.markdown(
            """
            The **median earnings 10 years after enrollment** is reported by the U.S. Department
            of Education. It reflects the midpoint salary of all students who attended that school
            (not just graduates), 10 years after they first enrolled.

            This is a real-world outcome measure — it captures what students are actually earning,
            not what the school claims they'll earn.
            """
        )
else:
    with st.expander("什麼是「實際學費」？為什麼不用標示學費？"):
        st.markdown(
            """
            **實際學費（Net Price）** 是學生在扣除助學金與獎學金後實際支付的平均金額，
            比標示學費更能反映真實負擔。

            例如，一所學校標示學費 $60,000/年，但平均學生在助學金後只需付 $25,000。
            我們盡量使用實際學費作為計算基礎。

            > 資料來源：College Scorecard 統計的是首次全職就讀、獲得聯邦助學資格學生的實際學費。
            """
        )
    with st.expander("「10年後薪資」是什麼意思？"):
        st.markdown(
            """
            **入學 10 年後的中位薪資** 由美國教育部提供，反映所有曾就讀該校學生
            （包含未畢業者）在入學 10 年後的薪資中位數。

            這是真實的就業結果數據——反映學生的實際薪資，而非學校的宣傳數字。
            """
        )

st.markdown("---")
st.caption(
    "Built by Yun-Ting Su | Boston University MSBA | "
    "Data: U.S. Dept. of Education College Scorecard + IPEDS"
)
