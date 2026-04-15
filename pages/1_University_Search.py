"""
Page 1 — School Profile
Search any U.S. college and get an integrated view of tuition, ROI, and scholarship options.
"""

import streamlit as st
from utils.theme import get_theme_css
import pandas as pd
import plotly.express as px
from utils.translations import t, US_STATES
from utils.api import search_schools, results_to_df, fmt_usd, fmt_pct, get_school_programs
from utils.calculations import (
    enrich_df, score_label, debt_label, cp_animal_badge_html, get_cp_animal,
    programs_to_df, CRED_LEVEL_MAP, CRED_LEVEL_MAP_ZH,
)
from utils.scholarships import EXTERNAL_SCHOLARSHIPS

st.set_page_config(page_title="School Profile", page_icon="🔍", layout="wide")
st.markdown(get_theme_css(), unsafe_allow_html=True)


lang = st.session_state.get("lang", "en")

with st.sidebar:
    st.caption(t("data_source", lang))

st.title(f"🔍 {t('search_title', lang)}")
st.markdown(t("search_desc", lang))
st.markdown("---")

# ── Search controls ───────────────────────────────────────────────────────────
sc1, sc2 = st.columns([4, 1])
with sc1:
    query = st.text_input(
        t("school_name", lang),
        placeholder=t("search_placeholder", lang),
    )
with sc2:
    state_filter = st.selectbox(t("filter_state", lang), US_STATES)

if not query and state_filter == "All":
    st.info(
        "Enter a school name above to get started — e.g. **Boston University**, **UCLA**, **MIT**."
        if lang == "en"
        else "請在上方輸入學校名稱開始搜尋，例如：**Boston University**、**UCLA**、**MIT**。"
    )
    st.stop()

# ── Fetch results ─────────────────────────────────────────────────────────────
with st.spinner(t("loading", lang)):
    results, total = search_schools(
        name=query,
        state="" if state_filter == "All" else state_filter,
        per_page=20,
    )

if not results:
    st.warning(
        f"No results for **\"{query}\"**. Check spelling or try an abbreviation."
        if lang == "en"
        else f"找不到 **\"{query}\"**，請確認拼寫。"
    )
    st.info(
        "Works with: full names, abbreviations (MIT, UCLA, NYU, BU), or Chinese (哈佛, 麻省理工, 東北大學)"
        if lang == "en"
        else "支援：全名、縮寫（MIT、UCLA、NYU、BU）、中文名稱（哈佛、麻省理工、波士頓大學）"
    )
    st.stop()

df = results_to_df(results)
df = enrich_df(df)

# ── School selector ───────────────────────────────────────────────────────────
st.markdown(
    f"**{total:,} {t('results_found', lang)}**"
    + (" — select one below to view the full profile." if lang == "en" else " — 選擇一所學校查看詳細資料。")
)

school_names = df["name"].dropna().tolist()
selected_name = st.selectbox(
    "Select a school / 選擇學校",
    ["— select —"] + school_names,
)

# Compact summary table (always visible)
type_col = "type_en" if lang == "en" else "type_zh"
display_df = df[["name", "state", type_col, "net_price", "earnings_10yr", "value_score"]].copy()
display_df.columns = [
    t("school_name", lang), t("state", lang), t("type", lang),
    t("net_price", lang), t("earnings_10yr", lang), t("value_score", lang),
]
display_df[t("net_price", lang)] = display_df[t("net_price", lang)].apply(fmt_usd)
display_df[t("earnings_10yr", lang)] = display_df[t("earnings_10yr", lang)].apply(fmt_usd)
display_df[t("value_score", lang)] = display_df[t("value_score", lang)].apply(
    lambda x: f"{x:.1f}" if pd.notna(x) and x is not None else "N/A"
)
st.dataframe(display_df, use_container_width=True, hide_index=True, height=220)

if selected_name == "— select —":
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# FULL INTEGRATED SCHOOL PROFILE
# ══════════════════════════════════════════════════════════════════════════════
row = df[df["name"] == selected_name].iloc[0]

st.markdown("---")

# ── Header ────────────────────────────────────────────────────────────────────
h1, h2 = st.columns([3, 1])
with h1:
    inst_type = row["type_en"] if lang == "en" else row["type_zh"]
    st.markdown(f"## {row['name']}")
    st.markdown(f"**{row.get('city', '')}, {row.get('state', '')}** · *{inst_type}*")
    if row.get("enrollment"):
        st.caption(
            f"{t('enrollment', lang)}: {int(row['enrollment']):,}"
            + (f"  ·  Avg SAT: {int(row['sat_avg'])}" if row.get("sat_avg") else "")
        )
with h2:
    school_url = row.get("url")
    npc_url = row.get("npc_url")
    if pd.notna(school_url) and school_url:
        st.link_button(
            t("visit_website", lang),
            f"https://{school_url}" if not str(school_url).startswith("http") else school_url,
        )
    if pd.notna(npc_url) and npc_url:
        st.link_button(t("net_price_calc", lang), npc_url)

st.markdown("---")

# ── Section 1: Tuition + Employment ──────────────────────────────────────────
cost_col, earn_col = st.columns(2)

with cost_col:
    st.subheader("💰 " + ("Tuition & Costs" if lang == "en" else "學費與費用"))
    m1, m2 = st.columns(2)
    with m1:
        st.metric(t("tuition_instate", lang), fmt_usd(row.get("tuition_in")))
        st.metric(t("net_price", lang), fmt_usd(row.get("net_price")))
    with m2:
        st.metric(t("tuition_outstate", lang), fmt_usd(row.get("tuition_out")))
        st.metric(t("median_debt", lang), fmt_usd(row.get("median_debt")))

with earn_col:
    st.subheader("📊 " + ("Employment Outcomes" if lang == "en" else "就業結果"))
    m3, m4 = st.columns(2)
    with m3:
        st.metric(t("earnings_6yr", lang), fmt_usd(row.get("earnings_6yr")))
        st.metric(t("completion_rate", lang), fmt_pct(row.get("completion_rate")))
    with m4:
        st.metric(t("earnings_10yr", lang), fmt_usd(row.get("earnings_10yr")))
        st.metric(t("admission_rate", lang), fmt_pct(row.get("admission_rate")))

# ── Section 2: CP Value ───────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🎯 " + ("CP Value Analysis" if lang == "en" else "CP 值分析"))

# Animal mascot badge
vs = row.get("value_score")
st.markdown(cp_animal_badge_html(vs, lang), unsafe_allow_html=True)

# Supporting metrics as HTML flex cards (no columns = no overlap)
dti = row.get("debt_to_income")
py  = row.get("payback_years")
dti_label = debt_label(dti, lang) if dti else "N/A"
py_label  = (f"{py:.1f} yrs" if lang == "en" else f"{py:.1f} 年") if py else "N/A"

metrics_html = f"""
<div style="display:flex;flex-wrap:wrap;gap:12px;margin:16px 0;">
    <div style="flex:1;min-width:180px;background:white;border:2.5px solid #1A1A1A;
        border-radius:12px;padding:14px 16px;">
        <div style="font-family:'Nunito',sans-serif;font-weight:800;font-size:0.75rem;
            text-transform:uppercase;letter-spacing:0.5px;color:#666;margin-bottom:4px;">
            {t('debt_to_income', lang)}
        </div>
        <div style="font-family:'Fredoka One',cursive;font-size:1.4rem;color:#1A1A1A;">
            {dti_label}
        </div>
    </div>
    <div style="flex:1;min-width:180px;background:white;border:2.5px solid #1A1A1A;
        border-radius:12px;padding:14px 16px;">
        <div style="font-family:'Nunito',sans-serif;font-weight:800;font-size:0.75rem;
            text-transform:uppercase;letter-spacing:0.5px;color:#666;margin-bottom:4px;">
            {'Payback Years' if lang == 'en' else '回本年數'}
        </div>
        <div style="font-family:'Fredoka One',cursive;font-size:1.4rem;color:#1A1A1A;">
            {py_label}
        </div>
    </div>
</div>
"""
st.markdown(metrics_html, unsafe_allow_html=True)
st.caption(
    "Value Score = 10yr earnings ÷ net price × graduation rate. Higher is better."
    if lang == "en"
    else "CP 值分數 = 10 年後薪資 ÷ 實際學費 × 畢業率。分數越高越好。"
)

# Cost vs Earnings bar chart
net_price = row.get("net_price")
earnings_6 = row.get("earnings_6yr")
earnings_10 = row.get("earnings_10yr")

if any([net_price, earnings_6, earnings_10]):
    chart_rows = []
    if net_price:
        chart_rows.append({
            "Label": ("Annual Net Price" if lang == "en" else "年均實際學費"),
            "Value": net_price,
            "Category": "Cost" if lang == "en" else "成本",
        })
    if earnings_6:
        chart_rows.append({
            "Label": ("Earnings (6yr)" if lang == "en" else "薪資（6年後）"),
            "Value": earnings_6,
            "Category": "Earnings" if lang == "en" else "薪資",
        })
    if earnings_10:
        chart_rows.append({
            "Label": ("Earnings (10yr)" if lang == "en" else "薪資（10年後）"),
            "Value": earnings_10,
            "Category": "Earnings" if lang == "en" else "薪資",
        })

    chart_df = pd.DataFrame(chart_rows)
    cat_en = {"Cost": "#E07070", "Earnings": "#5AB5A0"}
    cat_zh = {"成本": "#E07070", "薪資": "#5AB5A0"}
    color_map = cat_en if lang == "en" else cat_zh
    fig = px.bar(
        chart_df, x="Label", y="Value", color="Category",
        color_discrete_map=color_map,
        labels={"Value": "USD ($)", "Label": "", "Category": ""},
        height=300,
    )
    fig.update_yaxes(tickprefix="$", tickformat=",")
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.4),
        margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Value Score = 10yr earnings ÷ net price × graduation rate. Higher is better."
        if lang == "en"
        else "CP 值分數 = 10 年後薪資 ÷ 實際學費 × 畢業率。分數越高越好。"
    )

# ── Section 3: Programs & Fields of Study ────────────────────────────────────
st.markdown("---")
st.subheader("🎓 " + t("programs_title", lang))
st.caption(t("programs_desc", lang))

school_id = row.get("id")
if school_id:
    with st.spinner(t("programs_loading", lang)):
        raw_programs = get_school_programs(int(school_id))

    if raw_programs:
        prog_df = programs_to_df(
            raw_programs,
            school_net_price=row.get("net_price"),
            school_completion_rate=row.get("completion_rate"),
        )

        # ── Credential level filter ───────────────────────────────────────────
        cred_label_col = "cred_label" if lang == "en" else "cred_label_zh"
        all_creds = sorted(prog_df["cred_label"].dropna().unique().tolist())
        cred_display = {
            c: (CRED_LEVEL_MAP.get(k, c) if lang == "en" else CRED_LEVEL_MAP_ZH.get(k, c))
            for k, c in zip(prog_df["cred_level"].dropna().unique(), all_creds)
        }
        cred_options = [t("programs_cred_all", lang)] + all_creds
        selected_cred = st.selectbox(t("programs_filter_cred", lang), cred_options)

        # ── Sort ──────────────────────────────────────────────────────────────
        sort_options = {
            t("programs_sort_earn", lang): "median_earnings",
            t("programs_sort_debt", lang): "median_debt",
            t("programs_sort_ratio", lang): "prog_debt_ratio",
        }
        selected_sort_label = st.radio(
            t("programs_sort", lang),
            list(sort_options.keys()),
            horizontal=True,
        )
        sort_col = sort_options[selected_sort_label]

        # ── Filter & sort ─────────────────────────────────────────────────────
        display_prog = prog_df.copy()
        if selected_cred != t("programs_cred_all", lang):
            display_prog = display_prog[display_prog["cred_label"] == selected_cred]

        display_prog = display_prog.dropna(subset=["median_earnings"]).sort_values(
            sort_col, ascending=(sort_col != "median_earnings"), na_position="last"
        )

        if display_prog.empty:
            st.info(t("programs_no_data", lang))
        else:
            # Format for display
            show_cols = {
                t("programs_cip", lang): display_prog["cip_title"],
                t("programs_cred", lang): (
                    display_prog["cred_label"] if lang == "en" else display_prog["cred_label_zh"]
                ),
                t("programs_earn", lang): display_prog["median_earnings"].apply(
                    lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
                ),
                t("programs_debt", lang): display_prog["median_debt"].apply(
                    lambda x: fmt_usd(x) if pd.notna(x) else "N/A"
                ),
                t("programs_ratio", lang): display_prog["prog_debt_ratio"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) and x is not None else "N/A"
                ),
            }
            if "prog_value_score" in display_prog.columns:
                show_cols["CP"] = display_prog["prog_value_score"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) and x is not None else "N/A"
                )
                show_cols["🐾"] = display_prog.get("prog_animal", pd.Series(["🐾"] * len(display_prog)))

            table_df = pd.DataFrame(show_cols)
            st.dataframe(table_df, use_container_width=True, hide_index=True, height=320)
            st.caption(
                f"Showing {len(display_prog)} programs. "
                "Data: College Scorecard Field of Study (U.S. Dept. of Education)"
                if lang == "en"
                else f"顯示 {len(display_prog)} 個科系。資料來源：College Scorecard 科系層級資料（美國教育部）"
            )

            # ── Bachelor's vs Graduate earnings chart ─────────────────────────
            st.markdown("#### " + t("programs_vs_title", lang))
            st.caption(t("programs_vs_desc", lang))

            # Find fields that have both undergrad (cred_level=3) and grad (6 or 7)
            ug_progs = prog_df[prog_df["cred_level"] == 3][["cip_title", "median_earnings"]].rename(
                columns={"median_earnings": "bachelor_earn"}
            )
            ms_progs = prog_df[prog_df["cred_level"] == 6][["cip_title", "median_earnings"]].rename(
                columns={"median_earnings": "master_earn"}
            )
            phd_progs = prog_df[prog_df["cred_level"] == 7][["cip_title", "median_earnings"]].rename(
                columns={"median_earnings": "doctoral_earn"}
            )

            merged = ug_progs.merge(ms_progs, on="cip_title", how="outer")
            merged = merged.merge(phd_progs, on="cip_title", how="outer")
            # Keep only rows with at least 2 credential levels with data
            merged = merged.dropna(subset=["cip_title"])
            merged["data_count"] = merged[["bachelor_earn","master_earn","doctoral_earn"]].notna().sum(axis=1)
            merged = merged[merged["data_count"] >= 2].sort_values("bachelor_earn", ascending=False).head(15)

            if not merged.empty:
                chart_data = []
                for _, mrow in merged.iterrows():
                    if pd.notna(mrow.get("bachelor_earn")):
                        chart_data.append({
                            "Field": mrow["cip_title"][:35] + ("..." if len(mrow["cip_title"]) > 35 else ""),
                            "Earnings": mrow["bachelor_earn"],
                            "Level": "Bachelor's" if lang == "en" else "學士",
                        })
                    if pd.notna(mrow.get("master_earn")):
                        chart_data.append({
                            "Field": mrow["cip_title"][:35] + ("..." if len(mrow["cip_title"]) > 35 else ""),
                            "Earnings": mrow["master_earn"],
                            "Level": "Master's" if lang == "en" else "碩士",
                        })
                    if pd.notna(mrow.get("doctoral_earn")):
                        chart_data.append({
                            "Field": mrow["cip_title"][:35] + ("..." if len(mrow["cip_title"]) > 35 else ""),
                            "Earnings": mrow["doctoral_earn"],
                            "Level": "Doctoral" if lang == "en" else "博士",
                        })

                level_colors = {
                    "Bachelor's": "#4D96FF", "Master's": "#6BCB77", "Doctoral": "#9B5DE5",
                    "學士": "#4D96FF", "碩士": "#6BCB77", "博士": "#9B5DE5",
                }
                chart_df_prog = pd.DataFrame(chart_data)
                fig_prog = px.bar(
                    chart_df_prog,
                    x="Earnings", y="Field", color="Level",
                    barmode="group", orientation="h",
                    color_discrete_map=level_colors,
                    labels={
                        "Earnings": "Median Earnings (USD)" if lang == "en" else "薪資中位數（美元）",
                        "Field": "",
                        "Level": "Credential" if lang == "en" else "學位",
                    },
                    height=max(300, len(merged) * 45),
                )
                fig_prog.update_xaxes(tickprefix="$", tickformat=",")
                fig_prog.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Nunito", size=12),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25),
                    margin=dict(t=10, l=10),
                )
                st.plotly_chart(fig_prog, use_container_width=True)
            else:
                st.info(
                    "Not enough multi-level data to show a comparison chart for this school."
                    if lang == "en"
                    else "此校資料不足，無法顯示學位層級薪資比較圖。"
                )
    else:
        st.info(t("programs_no_data", lang))

# ── Section 4: Scholarship Recommendations ───────────────────────────────────
st.markdown("---")
st.subheader("🎓 " + ("Recommended Aid & Scholarships" if lang == "en" else "推薦助學方案"))

pell_rate = row.get("pell_rate") or 0

# Federal Aid / FAFSA callout
if pell_rate > 0.25:
    st.success(
        f"**{'Need-Based Aid Alert' if lang == 'en' else 'Pell 資格提示'}** — "
        + (f"{fmt_pct(pell_rate)} of students at this school receive Pell Grants. "
           "You likely qualify for need-based federal aid — file FAFSA as early as possible."
           if lang == "en"
           else f"此校 {fmt_pct(pell_rate)} 的學生獲得 Pell Grant，"
           "顯示有高比例學生具備財務需求資格。請盡早申請 FAFSA。")
    )
else:
    st.info(
        "**FAFSA**: File every year to access federal grants and loans — it's free and takes ~30 minutes."
        if lang == "en"
        else "**FAFSA**：每年申請以取得聯邦助學金與貸款資格，免費且約需 30 分鐘。"
    )

# School-specific links as HTML flex row
fafsa_btn_label = "Apply at studentaid.gov" if lang == "en" else "前往 studentaid.gov 申請"
fafsa_title = "FAFSA Application" if lang == "en" else "FAFSA 申請"
npc_title = "Estimate Your Cost" if lang == "en" else "估算你的實際費用"

st.markdown(f"**{fafsa_title}**")
st.link_button(fafsa_btn_label, "https://studentaid.gov/h/apply-for-aid/fafsa")

if pd.notna(npc_url) and npc_url:
    st.markdown(f"**{npc_title}**")
    st.link_button(t("open_npc", lang), npc_url)

st.markdown("---")

# External Scholarship Recommendations
st.markdown("#### " + ("External Scholarships" if lang == "en" else "外部獎學金推薦"))
st.caption(
    "These scholarships apply regardless of which school you attend:"
    if lang == "en"
    else "以下獎學金不限就讀學校，皆可申請："
)

# Show top 5 scholarships as HTML cards (no columns = no overlap)
sorted_scholarships = sorted(EXTERNAL_SCHOLARSHIPS, key=lambda s: (not s["intl_eligible"], s["name"]))
for s in sorted_scholarships[:5]:
    name = s["name"] if lang == "en" else s["name_zh"]
    amount = s["amount"] if lang == "en" else s["amount_zh"]
    elig = s["eligibility"] if lang == "en" else s["eligibility_zh"]
    badge = "🌏" if s["intl_eligible"] else "🇺🇸"
    intl_text = ("Yes ✅" if s["intl_eligible"] else "No ❌")
    elig_label = "Eligibility" if lang == "en" else "資格"
    deadline_label = "Deadline" if lang == "en" else "截止日期"
    intl_label = "Open to international students" if lang == "en" else "開放國際學生"
    apply_label = "Apply / 申請"

    st.markdown(
        f'<div style="background:white;border:2.5px solid #1A1A1A;border-radius:12px;'
        f'padding:14px 18px;margin:8px 0;">'
        f'<div style="font-family:\'Fredoka One\',cursive;font-size:1.05rem;color:#1A1A1A;margin-bottom:8px;">'
        f'{badge} {name} &nbsp;<span style="background:#F0F0F0;border:1.5px solid #1A1A1A;'
        f'border-radius:6px;padding:2px 8px;font-size:0.85rem;">{amount}</span></div>'
        f'<div style="font-size:0.85rem;color:#333;font-family:\'Nunito\',sans-serif;line-height:1.6;">'
        f'<b>{elig_label}:</b> {elig}<br>'
        f'<b>{deadline_label}:</b> {s["deadline"]}<br>'
        f'<b>{intl_label}:</b> {intl_text}'
        f'</div></div>',
        unsafe_allow_html=True,
    )
    st.link_button(f"{apply_label} — {name}", s["url"])

st.page_link(
    "pages/3_Scholarship_Aid.py",
    label="→ " + ("View all scholarships & loan guide" if lang == "en" else "查看全部獎學金與貸款說明"),
)

# ── Section 5: Quick Loan Estimate ───────────────────────────────────────────
st.markdown("---")
st.subheader("🧮 " + ("Quick Loan Repayment Estimate" if lang == "en" else "快速貸款還款試算"))

if net_price:
    total_4yr = net_price * 4
    r = (6.53 / 100) / 12
    n = 10 * 12  # 10-year repayment
    monthly_est = total_4yr * r * (1 + r) ** n / ((1 + r) ** n - 1)
    total_paid = monthly_est * n
    total_interest = total_paid - total_4yr

    e1, e2, e3, e4 = st.columns(4)
    with e1:
        st.metric(
            "Est. 4-Year Cost" if lang == "en" else "估計四年總費用",
            fmt_usd(total_4yr),
        )
    with e2:
        st.metric(
            "Monthly Payment (10yr)" if lang == "en" else "月還款額（10 年期）",
            fmt_usd(monthly_est),
        )
    with e3:
        st.metric(
            "Total Interest Paid" if lang == "en" else "總利息",
            fmt_usd(total_interest),
        )
    with e4:
        # Recommend min salary: monthly payment should be ≤10% of gross monthly income
        min_salary = monthly_est * 12 / 0.10
        st.metric(
            "Min. Salary Recommended" if lang == "en" else "建議最低年薪",
            fmt_usd(min_salary),
            help=(
                "Rule of thumb: loan payments should be ≤10% of gross income"
                if lang == "en"
                else "經驗法則：每月還款不超過稅前收入的 10%"
            ),
        )

    st.caption(
        "Assumes full borrowing at federal rate 6.53%, 10-year standard repayment plan."
        if lang == "en"
        else "假設全額以聯邦利率 6.53% 借款，採標準 10 年還款計畫。"
    )

    if earnings_10:
        dti_ratio = (monthly_est * 12) / earnings_10
        if dti_ratio < 0.10:
            st.success(
                f"Your estimated annual payment ({fmt_usd(monthly_est * 12)}) is "
                f"{dti_ratio*100:.1f}% of 10yr median earnings — **comfortable**."
                if lang == "en"
                else f"估計年還款額（{fmt_usd(monthly_est * 12)}）占10年後薪資的 {dti_ratio*100:.1f}%——**負擔輕鬆**。"
            )
        elif dti_ratio < 0.15:
            st.warning(
                f"Your estimated annual payment is {dti_ratio*100:.1f}% of 10yr median earnings — **manageable but watch expenses**."
                if lang == "en"
                else f"估計年還款額占10年後薪資的 {dti_ratio*100:.1f}%——**可負擔，但需注意開銷**。"
            )
        else:
            st.error(
                f"Your estimated annual payment is {dti_ratio*100:.1f}% of 10yr median earnings — **consider income-driven repayment or more aid**."
                if lang == "en"
                else f"估計年還款額占10年後薪資的 {dti_ratio*100:.1f}%——**建議申請更多助學金或依收入還款計畫**。"
            )
else:
    st.info(
        "Net price data not available for this school — use the Net Price Calculator above for a personalized estimate."
        if lang == "en"
        else "此校淨學費資料暫不可用，請使用上方淨學費計算機取得個人化估算。"
    )
