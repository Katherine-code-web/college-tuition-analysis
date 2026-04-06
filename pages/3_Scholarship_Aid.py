"""
Page 3 — Scholarships & Financial Aid
Federal aid guide, external scholarships, and school-specific aid lookup.
"""

import streamlit as st
import pandas as pd
from utils.translations import t
from utils.api import search_schools, results_to_df, fmt_pct
from utils.scholarships import EXTERNAL_SCHOLARSHIPS, LOAN_TYPES

st.set_page_config(page_title="Scholarships & Aid", page_icon="🎓", layout="wide")

lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.caption(t("data_source", lang))

st.title(f"🎓 {t('aid_title', lang)}")
st.markdown(t("aid_desc", lang))
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    t("tab_federal", lang),
    t("tab_external", lang),
    t("tab_school", lang),
    t("tab_loans", lang),
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Federal Aid (FAFSA)
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader(t("federal_title", lang))
    st.markdown(t("federal_intro", lang))

    st.info(
        f"**{t('fafsa_deadline', lang)}:** {t('fafsa_deadline_val', lang)}  \n"
        f"🔗 [{t('fafsa_url', lang)}](https://studentaid.gov/h/apply-for-aid/fafsa)"
    )

    st.markdown("---")
    st.subheader(t("aid_types_title", lang))

    # Grants (don't repay)
    st.markdown("#### 🎁 Grants — No Repayment Required" if lang == "en"
                else "#### 🎁 助學金——無需償還")

    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown(f"**{t('pell_grant_title', lang)}**")
        st.markdown(t("pell_grant_desc", lang))
    with g2:
        st.markdown(f"**{t('seog_title', lang)}**")
        st.markdown(t("seog_desc", lang))
    with g3:
        st.markdown(f"**{t('work_study_title', lang)}**")
        st.markdown(t("work_study_desc", lang))

    st.markdown("---")
    st.markdown("#### 💳 Loans — Must Be Repaid" if lang == "en"
                else "#### 💳 助學貸款——需要償還")

    l1, l2, l3 = st.columns(3)
    with l1:
        st.markdown(f"**{t('subsidized_title', lang)}** ✅")
        st.markdown(t("subsidized_desc", lang))
    with l2:
        st.markdown(f"**{t('unsubsidized_title', lang)}**")
        st.markdown(t("unsubsidized_desc", lang))
    with l3:
        st.markdown(f"**{t('plus_title', lang)}**")
        st.markdown(t("plus_desc", lang))

    st.markdown("---")
    st.markdown(
        "### Income-Driven Repayment Plans" if lang == "en"
        else "### 依收入還款計畫（IDR）"
    )
    idr_data = {
        "Plan": ["SAVE", "PAYE", "IBR", "ICR"],
        "Payment Cap": ["5–10% of discretionary income", "10%", "10–15%", "20%"],
        "Forgiveness": ["10–25 years", "20 years", "20–25 years", "25 years"],
        "Who qualifies": ["All federal borrowers", "New borrowers (Oct 2007+)", "All federal borrowers", "All federal borrowers"],
    } if lang == "en" else {
        "計畫": ["SAVE", "PAYE", "IBR", "ICR"],
        "還款上限": ["可支配收入的 5–10%", "10%", "10–15%", "20%"],
        "免除年限": ["10–25 年", "20 年", "20–25 年", "25 年"],
        "資格": ["所有聯邦貸款人", "2007年10月後的新借款人", "所有聯邦貸款人", "所有聯邦貸款人"],
    }
    st.table(pd.DataFrame(idr_data))
    st.caption(
        "SAVE (Saving on a Valuable Education) is the newest and most generous plan as of 2024."
        if lang == "en"
        else "SAVE（節省寶貴教育支出計畫）是 2024 年最新且最優惠的計畫。"
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — External Scholarships
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader(t("external_title", lang))
    st.markdown(t("external_intro", lang))
    st.info(t("intl_note", lang))

    # Filter
    intl_only = st.checkbox(
        "Show international-student eligible only / 只顯示開放國際學生的獎學金",
        value=False,
    )

    filtered = (
        [s for s in EXTERNAL_SCHOLARSHIPS if s["intl_eligible"]]
        if intl_only
        else EXTERNAL_SCHOLARSHIPS
    )

    for s in filtered:
        name = s["name"] if lang == "en" else s["name_zh"]
        amount = s["amount"] if lang == "en" else s["amount_zh"]
        elig = s["eligibility"] if lang == "en" else s["eligibility_zh"]
        intl_badge = "🌏 " if s["intl_eligible"] else "🇺🇸 "

        with st.expander(f"{intl_badge}{name} — {amount}"):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"**{'Eligibility' if lang == 'en' else '資格'}:** {elig}")
                st.markdown(f"**{'Deadline' if lang == 'en' else '截止日期'}:** {s['deadline']}")
                st.markdown(f"**{'Open to international students' if lang == 'en' else '開放國際學生'}:** {'Yes ✅' if s['intl_eligible'] else 'No ❌'}")
            with col_b:
                st.link_button(
                    "Apply / 申請" if lang == "en" else "前往申請",
                    s["url"],
                )

    st.markdown("---")
    st.markdown(
        "### More Scholarship Search Engines" if lang == "en"
        else "### 更多獎學金搜尋引擎"
    )
    resources = [
        ("Fastweb", "https://www.fastweb.com/", "Largest free scholarship search database"),
        ("Scholarships.com", "https://www.scholarships.com/", "500,000+ scholarship listings"),
        ("College Board BigFuture", "https://bigfuture.collegeboard.org/scholarship-search", "Scholarship search by major/state"),
        ("International Student", "https://www.internationalstudent.com/scholarships/", "Scholarships specifically for international students"),
        ("EducationUSA", "https://educationusa.state.gov/", "U.S. State Dept resource for international students"),
    ]
    for name, url, desc in resources:
        st.markdown(f"- **[{name}]({url})** — {desc}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — School-Specific Aid
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader(t("school_aid_title", lang))
    st.markdown(t("school_aid_desc", lang))

    school_query = st.text_input(
        t("school_aid_search", lang),
        placeholder=t("school_aid_search", lang),
        key="aid_school_search",
    )

    if school_query:
        with st.spinner(t("loading", lang)):
            results, _ = search_schools(name=school_query, per_page=8)

        if results:
            df = results_to_df(results)

            for _, row in df.iterrows():
                with st.expander(f"**{row['name']}** — {row.get('city', '')}, {row.get('state', '')}"):
                    ec1, ec2 = st.columns([2, 1])
                    with ec1:
                        st.markdown(f"**Type:** {row.get('type_en' if lang == 'en' else 'type_zh', 'N/A')}")

                        pell = row.get("pell_rate")
                        loan = row.get("loan_rate")
                        if pell:
                            st.markdown(f"**{fmt_pct(pell)}** {t('pell_recipients', lang)}")
                        if loan:
                            st.markdown(f"**{fmt_pct(loan)}** {t('loan_recipients', lang)}")

                    with ec2:
                        npc = row.get("npc_url")
                        aid = row.get("aid_url")
                        url = row.get("url")

                        if npc:
                            st.link_button(t("open_npc", lang), npc)
                        if aid:
                            st.link_button(
                                "Financial Aid Office" if lang == "en" else "助學金辦公室",
                                f"https://{aid}" if not str(aid).startswith("http") else aid,
                            )
                        elif url:
                            st.link_button(
                                t("visit_website", lang),
                                f"https://{url}" if not str(url).startswith("http") else url,
                            )
        else:
            st.warning(t("no_results", lang))

    st.markdown("---")
    st.markdown(
        "### Tips for Maximizing Aid / 助學金申請技巧" if lang == "en"
        else "### 助學金申請技巧"
    )
    tips_en = [
        "Apply for FAFSA **as early as possible** (opens October 1 each year)",
        "Apply to **several schools** — compare financial aid offers before committing",
        "**Negotiate** your aid package — schools often match competitor offers",
        "Look for **merit scholarships** even if you don't demonstrate financial need",
        "Check if your home country has **bilateral education agreements** with the U.S.",
        "Ask about **Graduate Assistantships** (TA/RA) for graduate programs — covers tuition + stipend",
    ]
    tips_zh = [
        "盡早申請 FAFSA（每年 10 月 1 日開放）",
        "同時申請多所學校，比較助學金方案後再決定",
        "與學校**談判**助學金——許多學校會配合競爭者的方案",
        "即使無財務需求，也要查詢**學術成就獎學金**",
        "確認你的國家是否與美國有**雙邊教育協議**",
        "詢問研究所的**助教/研究助理（TA/RA）職位**——通常包含學費減免與生活費補助",
    ]
    tips = tips_en if lang == "en" else tips_zh
    for tip in tips:
        st.markdown(f"- {tip}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Loan Types
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader(t("loans_title", lang))

    st.markdown(
        "> **Rule of thumb:** Try to borrow no more than your expected **first year's salary** in total. "
        "If your projected starting salary is $55,000, aim for ≤ $55,000 in total loans."
        if lang == "en"
        else "> **經驗法則：** 嘗試讓總貸款額不超過你的**預期第一年薪資**。"
             "如果你的預期起薪是 $55,000，總貸款目標 ≤ $55,000。"
    )

    st.markdown("---")
    st.subheader(t("loan_compare_title", lang))

    loan_rows = []
    for l in LOAN_TYPES:
        loan_rows.append({
            "Type" if lang == "en" else "類型": l["type"] if lang == "en" else l["type_zh"],
            "Max/Year" if lang == "en" else "年度上限": l["max_annual"],
            "2024–25 Rate" if lang == "en" else "2024–25 利率": l["rate_2024"],
            "Interest while in school" if lang == "en" else "在校期間利息": l["interest_during_school"] if lang == "en" else l["interest_during_school_zh"],
            "Repayment starts" if lang == "en" else "還款開始": l["repayment_starts"] if lang == "en" else l["repayment_starts_zh"],
            "Need-based?" if lang == "en" else "財務需求?": "Yes" if l["need_based"] else "No" if lang == "en" else ("是" if l["need_based"] else "否"),
        })

    st.table(pd.DataFrame(loan_rows))

    st.markdown("---")
    st.markdown("### Loan Repayment Calculator" if lang == "en" else "### 還款試算")

    calc_col1, calc_col2, calc_col3 = st.columns(3)
    with calc_col1:
        loan_amount = st.number_input(
            "Total loan amount ($)" if lang == "en" else "總貸款金額（美元）",
            min_value=0, max_value=300_000, value=30_000, step=1_000,
        )
    with calc_col2:
        interest_rate = st.number_input(
            "Interest rate (%)" if lang == "en" else "年利率（%）",
            min_value=0.0, max_value=20.0, value=6.53, step=0.1,
        )
    with calc_col3:
        repay_years = st.selectbox(
            "Repayment period (years)" if lang == "en" else "還款年限",
            [10, 20, 25], index=0,
        )

    if loan_amount > 0 and interest_rate > 0:
        r = (interest_rate / 100) / 12
        n = repay_years * 12
        monthly = loan_amount * r * (1 + r) ** n / ((1 + r) ** n - 1)
        total_paid = monthly * n
        total_interest = total_paid - loan_amount

        res1, res2, res3 = st.columns(3)
        with res1:
            st.metric(
                "Monthly Payment" if lang == "en" else "每月還款",
                f"${monthly:,.0f}",
            )
        with res2:
            st.metric(
                "Total Paid" if lang == "en" else "總還款金額",
                f"${total_paid:,.0f}",
            )
        with res3:
            st.metric(
                "Total Interest" if lang == "en" else "總利息",
                f"${total_interest:,.0f}",
                delta=f"+{total_interest/loan_amount*100:.1f}% over principal",
                delta_color="inverse",
            )
