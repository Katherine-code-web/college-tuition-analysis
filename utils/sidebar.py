"""
Shared sidebar widgets — import and call render_profile_status(lang)
inside any page's `with st.sidebar:` block.
"""

import streamlit as st


def render_profile_status(lang: str = "en") -> None:
    """
    Render a small profile status mini-card at the bottom of the sidebar.
    Shows a summary if profile is filled, or a prompt to fill it out.
    """
    profile = st.session_state.get("user_profile", {})

    st.markdown("---")

    if not profile.get("profile_complete"):
        st.markdown(
            "⚠️ **Profile not set**" if lang == "en" else "⚠️ **尚未設定條件**"
        )
        st.caption(
            "Fill it out for personalized recommendations."
            if lang == "en"
            else "填寫後可獲得個人化學校推薦。"
        )
        if st.button(
            "📝 Set My Profile" if lang == "en" else "📝 填寫我的條件",
            key="sidebar_profile_set_btn",
            use_container_width=False,
        ):
            st.switch_page("pages/7_My_Profile.py")
    else:
        gpa = profile.get("gpa")
        budget = profile.get("annual_budget", 0)
        lang_test = profile.get("language_test", "")
        lang_score = profile.get("language_score", "")
        degree = profile.get("target_degree", "")

        gpa_str = f"GPA {gpa:.1f}" if gpa else ""
        budget_str = f"${budget // 1000:.0f}k/yr" if budget else ""
        test_str = f"{lang_test.split()[0]} {lang_score}" if lang_score else ""

        summary_parts = [p for p in [degree, gpa_str, test_str, budget_str] if p]
        summary = " · ".join(summary_parts)

        st.markdown(f"✅ **{summary}**")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                "✏️ Edit" if lang == "en" else "✏️ 編輯",
                key="sidebar_profile_edit_btn",
                use_container_width=False,
            ):
                st.switch_page("pages/7_My_Profile.py")
        with col_b:
            if st.button(
                "🎯 Match" if lang == "en" else "🎯 配對",
                key="sidebar_profile_match_btn",
                use_container_width=False,
            ):
                st.switch_page("pages/8_Smart_Matcher.py")
