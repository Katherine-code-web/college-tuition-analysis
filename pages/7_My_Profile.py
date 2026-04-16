"""
Page 7 — My Profile
Enter your academic profile and preferences for personalized school recommendations.
"""

import streamlit as st
from datetime import datetime
from utils.theme import get_theme_css
from utils.calculations import CIP_CATEGORIES, CIP_CATEGORIES_ZH
from utils.sidebar import render_profile_status

st.set_page_config(page_title="My Profile", page_icon="📝", layout="wide")
st.markdown(get_theme_css(), unsafe_allow_html=True)

lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.caption("Data: College Scorecard (U.S. Dept. of Education) + IPEDS")
    render_profile_status(lang)

US_STATES_LIST = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
]

if lang == "en":
    st.title("📝 My Profile")
    st.markdown(
        "Fill out your academic background to get **personalized school recommendations** "
        "from the Smart Matcher. Your data stays only in this browser session."
    )
else:
    st.title("📝 我的條件")
    st.markdown(
        "填寫你的學術背景，讓 **Smart Matcher** 為你推薦最適合的學校。"
        "資料僅儲存於本次瀏覽器 session，不會上傳。"
    )

st.markdown("---")

# Load any existing profile so the form pre-fills
existing = st.session_state.get("user_profile", {})

with st.form("profile_form"):

    # ── 1. Basic Information ───────────────────────────────────────────────────
    st.subheader("1️⃣  Basic Information" if lang == "en" else "1️⃣  基本資訊")

    c1, c2 = st.columns(2)
    with c1:
        nat_opts = [
            "United States", "Taiwan", "China", "South Korea",
            "India", "Japan", "Other International",
        ]
        nationality = st.selectbox(
            "Nationality / 國籍",
            nat_opts,
            index=nat_opts.index(existing.get("nationality", "United States"))
            if existing.get("nationality") in nat_opts else 0,
        )
        edu_opts = [
            "High School",
            "Bachelor's (in progress)",
            "Bachelor's (completed)",
            "Master's",
        ]
        current_edu = st.selectbox(
            "Current Education Level / 目前學歷",
            edu_opts,
            index=edu_opts.index(existing.get("current_edu", "High School"))
            if existing.get("current_edu") in edu_opts else 0,
        )

    with c2:
        deg_opts = ["Bachelor's", "Master's", "Doctoral", "MBA"]
        target_degree = st.selectbox(
            "Target Degree / 目標學位",
            deg_opts,
            index=deg_opts.index(existing.get("target_degree", "Bachelor's"))
            if existing.get("target_degree") in deg_opts else 0,
        )
        term_opts = [
            "Fall 2025", "Spring 2026", "Fall 2026",
            "Spring 2027", "Fall 2027", "Fall 2028",
        ]
        target_term = st.selectbox(
            "Target Start Term / 預計入學學期",
            term_opts,
            index=term_opts.index(existing.get("target_term", "Fall 2026"))
            if existing.get("target_term") in term_opts else 2,
        )

    # Field of study — linked to CIP categories
    cip_keys = list(CIP_CATEGORIES.keys())
    cip_labels = list(CIP_CATEGORIES.values()) if lang == "en" else list(CIP_CATEGORIES_ZH.values())
    existing_cip = existing.get("target_field_cip", cip_keys[10])  # default: Computer Science
    field_idx = cip_keys.index(existing_cip) if existing_cip in cip_keys else 10
    selected_field_label = st.selectbox(
        "Target Field of Study / 目標科系",
        cip_labels,
        index=field_idx,
    )
    target_field_cip = cip_keys[cip_labels.index(selected_field_label)]

    st.markdown("---")

    # ── 2. Academic Record ─────────────────────────────────────────────────────
    st.subheader("2️⃣  Academic Record" if lang == "en" else "2️⃣  學業成績")

    c3, c4 = st.columns(2)
    with c3:
        use_100 = st.checkbox(
            "Use 100-point scale / 使用百分制",
            value=existing.get("use_100_scale", False),
        )
        if use_100:
            score_100 = st.number_input(
                "Score (0–100) / 百分制成績",
                min_value=0.0, max_value=100.0,
                value=float(existing.get("score_100") or 85.0),
                step=0.5,
            )
            gpa = round((score_100 / 100) * 4.0, 2)
            st.caption(f"≈ {gpa:.2f} / 4.0 (rough conversion: score ÷ 100 × 4)")
        else:
            gpa = st.number_input(
                "GPA (0.0 – 4.0)",
                min_value=0.0, max_value=4.0,
                value=float(existing.get("gpa") or 3.5),
                step=0.01,
            )
            score_100 = None

    with c4:
        class_rank = st.number_input(
            "Class Rank — Top % (optional) / 班級排名 top %（選填）",
            min_value=0.0, max_value=100.0,
            value=float(existing.get("class_rank") or 0.0),
            step=1.0,
            help="Enter 10 if you are in the top 10% of your class. Leave 0 if unknown.",
        )

    st.markdown("---")

    # ── 3. Language Proficiency ────────────────────────────────────────────────
    st.subheader("3️⃣  Language Proficiency" if lang == "en" else "3️⃣  語言檢定")

    c5, c6 = st.columns(2)
    with c5:
        lang_opts = [
            "None / Native Speaker",
            "TOEFL iBT",
            "IELTS",
            "Duolingo English Test",
        ]
        language_test = st.selectbox(
            "Language Test / 語言測驗",
            lang_opts,
            index=lang_opts.index(existing.get("language_test", "None / Native Speaker"))
            if existing.get("language_test") in lang_opts else 0,
        )
    with c6:
        if language_test == "TOEFL iBT":
            language_score = st.number_input(
                "TOEFL Score (0–120)",
                min_value=0, max_value=120,
                value=int(existing.get("language_score", 100) or 100),
                step=1,
            )
        elif language_test == "IELTS":
            language_score = st.number_input(
                "IELTS Score (0–9)",
                min_value=0.0, max_value=9.0,
                value=float(existing.get("language_score", 7.0) or 7.0),
                step=0.5,
            )
        elif language_test == "Duolingo English Test":
            language_score = st.number_input(
                "Duolingo Score (10–160)",
                min_value=10, max_value=160,
                value=int(existing.get("language_score", 120) or 120),
                step=5,
            )
        else:
            language_score = None
            st.caption(
                "Native speaker — no test required."
                if lang == "en"
                else "母語人士或免語言測驗。"
            )

    st.markdown("---")

    # ── 4. Standardized Tests (dynamic by degree) ─────────────────────────────
    st.subheader("4️⃣  Standardized Tests" if lang == "en" else "4️⃣  標準化測驗")

    sat_score = act_score = gre_score = gmat_score = None
    research_exp = ""

    if target_degree == "Bachelor's":
        c7, c8 = st.columns(2)
        with c7:
            sat_raw = st.number_input(
                "SAT Score (400–1600, optional) / SAT（選填）",
                min_value=0, max_value=1600,
                value=int(existing.get("sat") or 0),
                step=10,
                help="Leave 0 if not taken or test-optional.",
            )
            sat_score = sat_raw if sat_raw > 0 else None
        with c8:
            act_raw = st.number_input(
                "ACT Score (1–36, optional) / ACT（選填）",
                min_value=0, max_value=36,
                value=int(existing.get("act") or 0),
                step=1,
                help="Leave 0 if not taken.",
            )
            act_score = act_raw if act_raw > 0 else None

    elif target_degree in ("Master's", "MBA"):
        c7, c8 = st.columns(2)
        with c7:
            gre_raw = st.number_input(
                "GRE Total (260–340, optional) / GRE（選填）",
                min_value=0, max_value=340,
                value=int(existing.get("gre") or 0),
                step=1,
            )
            gre_score = gre_raw if gre_raw > 0 else None
        with c8:
            gmat_raw = st.number_input(
                "GMAT (200–800, optional) / GMAT（選填）",
                min_value=0, max_value=800,
                value=int(existing.get("gmat") or 0),
                step=10,
            )
            gmat_score = gmat_raw if gmat_raw > 0 else None

    elif target_degree == "Doctoral":
        gre_raw = st.number_input(
            "GRE Total (260–340, optional) / GRE（選填）",
            min_value=0, max_value=340,
            value=int(existing.get("gre") or 0),
            step=1,
        )
        gre_score = gre_raw if gre_raw > 0 else None
        research_exp = st.text_area(
            "Research Experience (optional) / 研究經歷（選填）",
            value=existing.get("research_exp", ""),
            height=90,
            placeholder="e.g. 2 years ML research, 1 publication in NeurIPS...",
        )

    st.markdown("---")

    # ── 5. Budget & Preferences ────────────────────────────────────────────────
    st.subheader("5️⃣  Budget & Preferences" if lang == "en" else "5️⃣  預算與偏好")
    st.caption(
        "💡 Include tuition + living expenses. International students typically need $30k–$80k/year."
        if lang == "en"
        else "💡 請包含學費與生活費。國際學生通常需要 $30k–$80k/year。"
    )

    annual_budget = st.slider(
        "Annual Budget (USD) / 年預算（美元）",
        min_value=0, max_value=100000,
        value=int(existing.get("annual_budget", 50000)),
        step=5000,
        format="$%d",
    )

    c9, c10 = st.columns(2)
    with c9:
        preferred_states = st.multiselect(
            "Preferred States (optional) / 偏好州別（選填）",
            US_STATES_LIST,
            default=existing.get("preferred_states", []),
        )
    with c10:
        type_opts = ["Any", "Public", "Private Nonprofit"]
        preferred_type = st.selectbox(
            "Preferred School Type / 偏好學校類型",
            type_opts,
            index=type_opts.index(existing.get("preferred_type", "Any"))
            if existing.get("preferred_type") in type_opts else 0,
        )

    st.markdown("---")

    # ── 6. Priority Weights ────────────────────────────────────────────────────
    st.subheader(
        "6️⃣  What Matters Most to You?" if lang == "en" else "6️⃣  什麼對你最重要？"
    )
    st.caption(
        "Rate each factor 1 (not important) → 5 (very important)."
        if lang == "en"
        else "為每個因素評分：1（不重要）→ 5（非常重要）。"
    )

    existing_w = existing.get("priority_weights", {})
    cp1, cp2, cp3, cp4 = st.columns(4)
    with cp1:
        w_cp = st.slider("📈 CP Value / ROI", 1, 5, value=int(existing_w.get("cp_value", 3)))
    with cp2:
        w_prestige = st.slider("🏆 Prestige", 1, 5, value=int(existing_w.get("prestige", 2)))
    with cp3:
        w_cost = st.slider("💰 Low Cost", 1, 5, value=int(existing_w.get("low_cost", 3)))
    with cp4:
        w_employment = st.slider("💼 Employment", 1, 5, value=int(existing_w.get("employment", 3)))

    st.markdown("---")

    submitted = st.form_submit_button(
        "✅ Save My Profile" if lang == "en" else "✅ 儲存條件",
        type="primary",
    )

# ── Save to session state ──────────────────────────────────────────────────────
if submitted:
    st.session_state["user_profile"] = {
        "nationality": nationality,
        "current_edu": current_edu,
        "target_degree": target_degree,
        "target_term": target_term,
        "target_field": CIP_CATEGORIES.get(target_field_cip, selected_field_label),
        "target_field_cip": target_field_cip,
        "gpa": gpa,
        "use_100_scale": use_100,
        "score_100": score_100,
        "class_rank": class_rank if class_rank > 0 else None,
        "language_test": language_test,
        "language_score": language_score,
        "sat": sat_score,
        "act": act_score,
        "gre": gre_score,
        "gmat": gmat_score,
        "research_exp": research_exp,
        "annual_budget": annual_budget,
        "preferred_states": preferred_states,
        "preferred_type": preferred_type,
        "priority_weights": {
            "cp_value": w_cp,
            "prestige": w_prestige,
            "low_cost": w_cost,
            "employment": w_employment,
        },
        "profile_complete": True,
        "updated_at": datetime.now().isoformat(),
    }
    st.success(
        "✅ Profile saved! Head to **Smart Matcher** to see your personalized recommendations."
        if lang == "en"
        else "✅ 條件已儲存！前往 **Smart Matcher** 查看個人化學校推薦。"
    )
    st.balloons()

# ── Profile Summary Card (shown after save or if profile exists) ───────────────
profile = st.session_state.get("user_profile", {})
if profile.get("profile_complete"):
    st.markdown("---")
    st.subheader("📋 Your Current Profile" if lang == "en" else "📋 目前的條件設定")

    def _row(label, value):
        return (
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px dashed #D4A574;">'
            f'<span style="color:#555;font-size:0.88rem;">{label}</span>'
            f'<span style="font-weight:800;font-size:0.9rem;">{value}</span>'
            f'</div>'
        )

    p = profile
    gpa_disp = f"{p.get('gpa', '?'):.2f} / 4.0" if p.get("gpa") else "—"
    score_disp = f"{p.get('score_100'):.1f}/100" if p.get("score_100") else "—"
    test_disp = (
        f"{p.get('language_test','')} {p.get('language_score','')}"
        if p.get("language_score")
        else "—"
    )
    sat_disp = str(p.get("sat")) if p.get("sat") else "—"
    act_disp = str(p.get("act")) if p.get("act") else "—"
    gre_disp = str(p.get("gre")) if p.get("gre") else "—"
    gmat_disp = str(p.get("gmat")) if p.get("gmat") else "—"
    budget_disp = f"${p.get('annual_budget', 0):,}/yr"
    states_disp = ", ".join(p.get("preferred_states", [])) or ("Any" if lang == "en" else "不限")
    w = p.get("priority_weights", {})
    weights_disp = (
        f"CP Value ×{w.get('cp_value',3)} · "
        f"Prestige ×{w.get('prestige',2)} · "
        f"Cost ×{w.get('low_cost',3)} · "
        f"Jobs ×{w.get('employment',3)}"
    )

    rows_html = "".join([
        _row("Nationality / 國籍", p.get("nationality", "—")),
        _row("Current Education / 目前學歷", p.get("current_edu", "—")),
        _row("Target Degree / 目標學位", p.get("target_degree", "—")),
        _row("Target Term / 預計入學", p.get("target_term", "—")),
        _row("Field of Study / 目標科系", p.get("target_field", "—")),
        _row("GPA", gpa_disp),
        _row("100-pt Score / 百分制", score_disp),
        _row("Language Test / 語言", test_disp),
        _row("SAT", sat_disp),
        _row("ACT", act_disp),
        _row("GRE", gre_disp),
        _row("GMAT", gmat_disp),
        _row("Annual Budget / 年預算", budget_disp),
        _row("Preferred States / 偏好州", states_disp),
        _row("School Type / 學校類型", p.get("preferred_type", "Any")),
        _row("Priority Weights / 優先排序", weights_disp),
    ])

    st.markdown(
        f'<div style="background:white;border:2.5px solid #1A1A1A;border-radius:14px;'
        f'box-shadow:5px 5px 0px #1A1A1A;padding:20px 24px;">'
        f'{rows_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button(
        "🎯 Go to Smart Matcher" if lang == "en" else "🎯 前往 Smart Matcher",
        type="primary",
    ):
        st.switch_page("pages/8_Smart_Matcher.py")
