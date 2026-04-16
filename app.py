"""
U.S. College Value & Scholarship Platform
Home page — entry point for Streamlit multipage app
"""

import streamlit as st
from utils.theme import get_theme_css
from utils.translations import t, T
from utils.advisors import ADVISORS, DEFAULT_ADVISOR
from utils.sidebar import render_profile_status

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="U.S. College ROI Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(get_theme_css(), unsafe_allow_html=True)


# ── Language selector (persisted in session state) ────────────────────────────
if "lang" not in st.session_state:
    st.session_state.lang = "en"

if "advisor" not in st.session_state:
    st.session_state.advisor = DEFAULT_ADVISOR

with st.sidebar:
    lang_choice = st.selectbox(
        "🌐 Language / 語言",
        ["English", "中文"],
        index=0 if st.session_state.lang == "en" else 1,
    )
    st.session_state.lang = "en" if lang_choice == "English" else "zh"
    lang = st.session_state.lang

    st.markdown("---")

    # Advisor selector
    st.markdown("**🐾 Choose Your Advisor / 選擇你的顧問**")
    advisor_keys = list(ADVISORS.keys())
    name_field = "animal_en" if lang == "en" else "animal_zh"
    advisor_labels = [
        f"{ADVISORS[k]['emoji']} {ADVISORS[k][name_field]}" for k in advisor_keys
    ]
    current_idx = advisor_keys.index(st.session_state.advisor) if st.session_state.advisor in advisor_keys else 0
    chosen_label = st.selectbox(
        "Advisor",
        advisor_labels,
        index=current_idx,
        label_visibility="collapsed",
    )
    chosen_key = advisor_keys[advisor_labels.index(chosen_label)]
    if chosen_key != st.session_state.advisor:
        st.session_state.advisor = chosen_key
        # Reset chat when advisor changes
        st.session_state.messages = []

    adv = ADVISORS[chosen_key]
    tagline_field = "tagline_en" if lang == "en" else "tagline_zh"
    name_field2 = "name_en" if lang == "en" else "name_zh"
    st.caption(f"*\"{adv[tagline_field]}\"*")

    st.markdown("---")
    st.caption(t("data_source", lang))
    render_profile_status(lang)

lang = st.session_state.lang

# ── Hero ──────────────────────────────────────────────────────────────────────
adv_home = ADVISORS[st.session_state.get("advisor", DEFAULT_ADVISOR)]
st.markdown(f"""
<div style="
    background: linear-gradient(135deg, #FF8C42, #FFD166);
    border: 3px solid #1A1A1A;
    border-radius: 18px;
    box-shadow: 6px 6px 0px #1A1A1A;
    padding: 32px 36px;
    margin-bottom: 24px;
">
    <div style="font-family:'Fredoka One',cursive; font-size:2.6rem; color:#1A1A1A; line-height:1.2;">
        {adv_home['emoji']} {t('app_title', lang)}
    </div>
    <div style="font-family:'Nunito',sans-serif; font-weight:800; font-size:1.1rem; color:#1A1A1A; margin-top:8px; opacity:0.85;">
        {t('app_subtitle', lang)}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Features grid — single HTML block, no columns ────────────────────────────
st.markdown(f"### ✨ {t('home_features', lang)}")

feat_items = [
    ("🔍", t('feat_search', lang),  "#DDEEFF", "#4D96FF"),
    ("📊", t('feat_roi', lang),     "#FFDDD8", "#E8503A"),
    ("🎓", t('feat_aid', lang),     "#DDFAE4", "#6BCB77"),
    ("📈", t('feat_trend', lang),   "#EDE0FF", "#9B5DE5"),
]

cards_html = "".join([
    f"""<div style="flex:1;min-width:180px;background:{bg};border:2.5px solid #1A1A1A;
        border-radius:14px;padding:20px 14px;text-align:center;margin:6px;">
        <div style="font-size:2rem;">{icon}</div>
        <div style="font-family:'Fredoka One',cursive;font-size:1rem;
            color:#1A1A1A;margin-top:8px;line-height:1.3;">{label}</div>
    </div>"""
    for icon, label, bg, color in feat_items
])

st.markdown(
    f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:24px;">{cards_html}</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# ── How CP Value works — single HTML block ────────────────────────────────────
if lang == "en":
    st.subheader("How We Calculate CP Value (ROI Score)")
    formulas = [
        ("📈", "Value Score", "10-yr Earnings ÷ Net Price", "Higher = better ROI per tuition dollar", "#DDFAE4"),
        ("💳", "Debt-to-Income", "Median Debt ÷ 10-yr Earnings", "Lower = more manageable after graduation", "#FFF5CC"),
        ("📅", "Payback Years", "(Net Price × 4) ÷ 10-yr Earnings", "Years of post-grad income to cover tuition", "#DDEEFF"),
    ]
else:
    st.subheader("CP 值計算方式")
    formulas = [
        ("📈", "CP 值分數", "10年後薪資 ÷ 實際年學費", "分數越高，每一塊學費買到的薪資潛力越大", "#DDFAE4"),
        ("💳", "負債收入比", "中位學貸 ÷ 10年後薪資", "比率越低，畢業後的還款壓力越小", "#FFF5CC"),
        ("📅", "回本年數", "（實際年學費 × 4）÷ 10年後薪資", "幾年薪資可以還清四年學費", "#DDEEFF"),
    ]

formula_html = "".join([
    f"""<div style="flex:1;min-width:220px;background:{bg};border:2.5px solid #1A1A1A;
        border-radius:14px;padding:18px 16px;margin:6px;">
        <div style="font-size:1.5rem;">{icon}</div>
        <div style="font-family:'Fredoka One',cursive;font-size:1.1rem;margin:6px 0 4px;">{name}</div>
        <div style="font-family:'Nunito',sans-serif;font-weight:800;font-size:0.95rem;
            background:white;border:2px solid #1A1A1A;border-radius:8px;
            padding:4px 10px;display:inline-block;margin-bottom:8px;">{formula}</div>
        <div style="font-size:0.82rem;color:#555;font-family:'Nunito',sans-serif;
            font-weight:700;">{caption}</div>
    </div>"""
    for icon, name, formula, caption, bg in formulas
])

st.markdown(
    f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:24px;">{formula_html}</div>',
    unsafe_allow_html=True,
)

st.markdown("---")
st.caption(
    "Built by Yun-Ting Su | Boston University MSBA | "
    "Data: U.S. Dept. of Education College Scorecard + IPEDS"
)
