"""
Page 5 — AI College Advisor
Chat with your chosen animal advisor powered by Gemini + real College Scorecard data.
"""

import os
import re
import json
import pandas as pd
import streamlit as st
from utils.theme import get_theme_css
import google.generativeai as genai
from dotenv import load_dotenv
from utils.api import search_schools, results_to_df, fmt_usd, fmt_pct, SCHOOL_ALIASES, get_school_programs
from utils.calculations import enrich_df, score_label, debt_label, programs_to_df, CRED_LEVEL_MAP
from utils.scholarships import EXTERNAL_SCHOLARSHIPS
from utils.advisors import ADVISORS, DEFAULT_ADVISOR, advisor_system_personality

load_dotenv()

st.set_page_config(page_title="AI College Advisor", page_icon="🤖", layout="wide")
st.markdown(get_theme_css(), unsafe_allow_html=True)

lang = st.session_state.get("lang", "en")
advisor_key = st.session_state.get("advisor", DEFAULT_ADVISOR)
adv = ADVISORS[advisor_key]

gemini_key = os.getenv("GEMINI_API_KEY", "")
if not gemini_key:
    st.error(
        "GEMINI_API_KEY not found. Add it to Streamlit Cloud Secrets."
        if lang == "en"
        else "找不到 GEMINI_API_KEY，請至 Streamlit Cloud Secrets 設定。"
    )
    st.stop()

genai.configure(api_key=gemini_key)

# ── Theme CSS ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
    .advisor-header {{
        background: linear-gradient(135deg, {adv['bg_color']} 0%, white 100%);
        border-left: 5px solid {adv['color']};
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 16px;
    }}
    .advisor-name {{
        font-size: 1.4rem;
        font-weight: 700;
        color: {adv['color']};
    }}
    .advisor-tagline {{
        font-size: 0.9rem;
        color: #666;
        font-style: italic;
    }}
</style>
""", unsafe_allow_html=True)

# ── Advisor header ─────────────────────────────────────────────────────────────
name_field = "name_en" if lang == "en" else "name_zh"
animal_field = "animal_en" if lang == "en" else "animal_zh"
tagline_field = "tagline_en" if lang == "en" else "tagline_zh"

st.markdown(f"""
<div class="advisor-header">
    <div class="advisor-name">{adv['emoji']} {adv[name_field]} &nbsp;<span style="font-weight:400;font-size:1rem;color:#888">— {adv[animal_field]}</span></div>
    <div class="advisor-tagline">"{adv[tagline_field]}"</div>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Powered by Claude + College Scorecard real-time data. Change advisor in the sidebar."
    if lang == "en"
    else "由 Claude + College Scorecard 即時資料驅動。可在左側選單切換顧問。"
)

# ── Suggested prompts ─────────────────────────────────────────────────────────
if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    st.markdown("---")
    st.markdown("**" + ("Try asking:" if lang == "en" else "你可以這樣問：") + "**")
    suggestions_en = [
        "Compare Harvard and MIT",
        "Which schools in California have the best ROI?",
        "Is a Master's degree in Computer Science at MIT worth it?",
        "What scholarships are available for international students?",
        "I have a $40,000/year budget — what are my options?",
        "Compare CS programs at CMU vs Georgia Tech",
    ]
    suggestions_zh = [
        "比較哈佛和MIT",
        "加州哪些學校 CP 值最高？",
        "MIT 的資訊科學碩士值得讀嗎？",
        "哪些獎學金開放國際學生申請？",
        "我的年預算是 $40,000，有哪些學校可以選？",
        "比較 CMU 和 Georgia Tech 的 CS 科系",
    ]
    suggestions = suggestions_en if lang == "en" else suggestions_zh
    cols = st.columns(2)
    for i, s in enumerate(suggestions):
        if cols[i % 2].button(s, key=f"suggest_{i}", use_container_width=True):
            if "messages" not in st.session_state:
                st.session_state.messages = []
            st.session_state.messages.append({"role": "user", "content": s})
            st.rerun()
    st.markdown("---")

# ── Chat history ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    avatar = adv["emoji"] if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ── Input ─────────────────────────────────────────────────────────────────────
user_input = st.chat_input(
    f"{adv['emoji']} Ask {adv[name_field]}..." if lang == "en"
    else f"{adv['emoji']} 問 {adv[name_field]}..."
)

if not user_input:
    st.stop()

st.session_state.messages.append({"role": "user", "content": user_input})
with st.chat_message("user", avatar="👤"):
    st.markdown(user_input)


# ── Step 1: Use Claude to extract school names from the query ──────────────────
def extract_school_names(text: str) -> list[str]:
    """
    Use Gemini Flash to extract all school names mentioned in the query.
    Returns a list of English school name strings to search.
    """
    extraction_prompt = (
        "Extract all U.S. university or college names from the following text. "
        "Return ONLY a JSON array of strings with the English search-friendly school names. "
        "Translate Chinese school names to English. Expand abbreviations (MIT → Massachusetts Institute of Technology, "
        "UCLA → University of California Los Angeles, NYU → New York University, BU → Boston University, etc.). "
        "If no school names are mentioned, return an empty array []. "
        "Examples:\n"
        "  Input: '比較波士頓大學和東北大學' → [\"Boston University\", \"Northeastern University\"]\n"
        "  Input: 'compare MIT and Harvard' → [\"Massachusetts Institute of Technology\", \"Harvard University\"]\n"
        "  Input: 'what scholarships exist for international students' → []\n"
        "  Input: '加州哪些學校CP值最高' → []\n"
        f"\nText: {text}\n\nReturn only the JSON array, nothing else."
    )
    try:
        flash_model = genai.GenerativeModel("gemini-2.0-flash")
        resp = flash_model.generate_content(extraction_prompt)
        raw = resp.text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
        names = json.loads(raw)
        return [n for n in names if isinstance(n, str) and len(n) > 2]
    except Exception:
        return []


# ── Step 2: Fetch data for each extracted school ───────────────────────────────
def fetch_school_data(query: str, per_page: int = 2) -> str:
    """Search for a school and return formatted data string including top programs."""
    results, _ = search_schools(name=query, per_page=per_page)
    if not results:
        return ""
    df = results_to_df(results)
    df = enrich_df(df)
    lines = []
    for _, row in df.iterrows():
        vs = row.get("value_score")
        dti = row.get("debt_to_income")
        py = row.get("payback_years")
        enrollment = row.get("enrollment")
        vs_str = f"{vs:.2f} ({score_label(vs, 'en')})" if vs else "N/A"
        dti_str = debt_label(dti, "en") if dti else "N/A"
        py_str = f"{py:.1f} years" if py else "N/A"
        enroll_str = f"{int(enrollment):,}" if enrollment else "N/A"
        school_block = (
            f"School: {row.get('name', 'Unknown')} ({row.get('state', '')}) — {row.get('type_en', '')}\n"
            f"  Enrollment: {enroll_str}\n"
            f"  Admission rate: {fmt_pct(row.get('admission_rate'))}\n"
            f"  In-state tuition: {fmt_usd(row.get('tuition_in'))} | Out-of-state: {fmt_usd(row.get('tuition_out'))}\n"
            f"  Avg net price (after aid): {fmt_usd(row.get('net_price'))}\n"
            f"  Median debt at graduation: {fmt_usd(row.get('median_debt'))}\n"
            f"  Earnings 6yr: {fmt_usd(row.get('earnings_6yr'))} | Earnings 10yr: {fmt_usd(row.get('earnings_10yr'))}\n"
            f"  Graduation rate: {fmt_pct(row.get('completion_rate'))}\n"
            f"  CP Value Score: {vs_str}\n"
            f"  Debt-to-Income: {dti_str}\n"
            f"  Payback years: {py_str}\n"
            f"  Pell Grant recipients: {fmt_pct(row.get('pell_rate'))} | Federal loan recipients: {fmt_pct(row.get('loan_rate'))}\n"
        )
        # Append top programs by credential level if available
        school_id = row.get("id")
        if school_id:
            try:
                raw_programs = get_school_programs(int(school_id))
                if raw_programs:
                    prog_df = programs_to_df(
                        raw_programs,
                        school_net_price=row.get("net_price"),
                        school_completion_rate=row.get("completion_rate"),
                    )
                    prog_df = prog_df.dropna(subset=["median_earnings"])
                    if not prog_df.empty:
                        prog_lines = ["  Top programs by credential level (1yr post-graduation earnings):"]
                        for cred_level in [3, 6, 7]:  # Bachelor's, Master's, Doctoral
                            cred_sub = prog_df[prog_df["cred_level"] == cred_level]
                            if not cred_sub.empty:
                                cred_name = CRED_LEVEL_MAP.get(cred_level, "Unknown")
                                top3 = cred_sub.nlargest(3, "median_earnings")
                                prog_lines.append(f"    {cred_name}:")
                                for _, pr in top3.iterrows():
                                    earn_str = fmt_usd(pr["median_earnings"])
                                    debt_str = fmt_usd(pr["median_debt"]) if pd.notna(pr.get("median_debt")) else "N/A"
                                    prog_lines.append(
                                        f"      - {pr['cip_title']}: earnings {earn_str}, debt {debt_str}"
                                    )
                        school_block += "\n".join(prog_lines) + "\n"
            except Exception:
                pass
        lines.append(school_block)
    return "\n".join(lines)


def get_scholarship_context() -> str:
    lines = ["Available external scholarships:"]
    for s in EXTERNAL_SCHOLARSHIPS:
        lines.append(
            f"- {s['name']}: {s['amount']} | Deadline: {s['deadline']} | "
            f"International eligible: {'Yes' if s['intl_eligible'] else 'No'} | {s['eligibility']}"
        )
    return "\n".join(lines)


# ── Fetch data with spinner ────────────────────────────────────────────────────
with st.spinner(
    f"{adv['emoji']} Looking up school data..." if lang == "en"
    else f"{adv['emoji']} 查詢學校資料中..."
):
    # Extract school names via Claude
    school_names = extract_school_names(user_input)

    school_data_context = ""
    fetched_schools = []

    if school_names:
        for name in school_names[:4]:  # max 4 schools per query
            data = fetch_school_data(name, per_page=1)
            if data:
                school_data_context += data + "\n"
                fetched_schools.append(name)

    # If Claude found no names or API returned nothing, try searching the raw query
    if not school_data_context:
        school_data_context = fetch_school_data(user_input, per_page=5)

    scholarship_context = get_scholarship_context()

# Show which schools were found (for transparency)
if fetched_schools:
    st.caption(
        f"Data fetched for: {', '.join(fetched_schools)}"
        if lang == "en"
        else f"已查詢資料：{', '.join(fetched_schools)}"
    )

# ── Build system prompt ────────────────────────────────────────────────────────
persona = advisor_system_personality(advisor_key, lang)

system_prompt = f"""You are an expert U.S. college advisor helping students (especially international and Taiwanese students) understand the real costs, ROI, and financial aid options for U.S. universities.

PERSONA — stay in character throughout every response:
{persona}

RULES:
- Base all financial numbers strictly on the real-time data provided below. Never fabricate figures.
- If data for a school is missing or shows N/A, say so clearly rather than guessing.
- Respond in the same language the user is using (English or Traditional Chinese).
- Use tables or bullet points for comparisons between multiple schools.
- Mention relevant scholarships when the user asks about costs or aid.

KEY METRICS EXPLAINED:
- CP Value Score = 10yr earnings ÷ net price × graduation rate. Higher is better.
  Score < 2: Low | 2–4: Fair | 4–6: Good | 6+: Excellent
- Debt-to-Income = median debt ÷ 10yr earnings. Below 1.0 manageable, above 1.5 risky.
- Payback Years = (net price × 4) ÷ 10yr earnings.
- Program-level earnings = 1-year post-completion median earnings by CIP field & credential level.
  Available for Bachelor's (level 3), Master's (level 6), and Doctoral (level 7) programs.
- Graduate Premium = (Master's earnings - Bachelor's earnings) per year.
  Payback = (extra tuition + opportunity cost) ÷ annual earnings premium.

--- REAL-TIME SCHOOL DATA ---
{school_data_context if school_data_context else "No specific school data was found for this query. Answer based on general knowledge and note the limitation."}

--- SCHOLARSHIP DATA ---
{scholarship_context}
"""

# ── Stream Gemini response ────────────────────────────────────────────────────
# Convert message history to Gemini format (role: "user"/"model", parts: [text])
gemini_history = []
for m in st.session_state.messages[-12:][:-1]:  # all except the last user message
    gemini_role = "model" if m["role"] == "assistant" else "user"
    gemini_history.append({"role": gemini_role, "parts": [m["content"]]})

advisor_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=system_prompt,
    generation_config=genai.GenerationConfig(max_output_tokens=1200),
)

chat_session = advisor_model.start_chat(history=gemini_history)

with st.chat_message("assistant", avatar=adv["emoji"]):
    response_placeholder = st.empty()
    full_response = ""

    try:
        stream = chat_session.send_message(user_input, stream=True)
        for chunk in stream:
            if chunk.text:
                full_response += chunk.text
                response_placeholder.markdown(full_response + "▌")
    except Exception as e:
        full_response = (
            "Sorry, I encountered an error. Please try again."
            if lang == "en"
            else "抱歉，發生錯誤，請再試一次。"
        )

    response_placeholder.markdown(full_response)

st.session_state.messages.append({"role": "assistant", "content": full_response})

# ── Clear chat ────────────────────────────────────────────────────────────────
st.markdown("---")
if st.button("🗑 Clear chat / 清除對話", key="clear_chat"):
    st.session_state.messages = []
    st.rerun()
