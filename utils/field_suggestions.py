"""
Hints shown in Smart Matcher when a field+credential combo has no data.

Many professional degrees (J.D., M.D.) are classified as "First Professional"
in College Scorecard, not Master's — so users selecting Law + Master's or
Medicine + Master's will often see 0 programs.
"""

# Maps CIP 2-digit prefix → hint text when no field data is found
FIELD_CREDENTIAL_HINTS: dict[str, dict] = {
    "22": {  # Law & Legal Studies
        "en": (
            "💡 **Most U.S. law degrees are J.D. (Juris Doctor)**, which is a "
            "First Professional degree — not a Master's. LL.M. (Master of Laws) "
            "cohort data is often suppressed due to small sample sizes.\n\n"
            "**Suggestion:** To find law schools, try changing your Target Degree "
            "to **Doctoral** in your profile. J.D. programs at ABA-accredited schools "
            "report earnings data under the Doctoral/Professional level."
        ),
        "zh": (
            "💡 **美國大多數法學學位是 J.D.（法律博士）**，屬於專業學位，不是碩士。"
            "LL.M.（法學碩士）因樣本數太小，薪資資料常被隱藏。\n\n"
            "**建議：** 若要找法學院，請在 Profile 將目標學位改為 **Doctoral（博士/專業學位）**。"
        ),
    },
    "51": {  # Medicine, Nursing & Health Professions
        "en": (
            "💡 **M.D. and D.O. medical degrees are First Professional degrees**, "
            "not Master's. College Scorecard often groups them with Doctoral-level programs.\n\n"
            "**Suggestion:** Try changing your Target Degree to **Doctoral** to find "
            "medical schools. For Master's-level health programs (M.S., M.P.H.), "
            "data coverage is limited for smaller cohorts."
        ),
        "zh": (
            "💡 **M.D. 和 D.O. 醫學學位是專業學位**，不是碩士。College Scorecard 通常將其歸入博士/專業學位類別。\n\n"
            "**建議：** 若要找醫學院，請將目標學位改為 **Doctoral**。碩士程度的健康科學（M.S.、M.P.H.）"
            "因樣本數小，資料覆蓋率有限。"
        ),
    },
    "52": {  # Business, Management & MBA
        "en": (
            "💡 **MBA program earnings data is often incomplete** in College Scorecard. "
            "Top programs (Harvard, Wharton, Booth) sometimes have suppressed data "
            "due to privacy protections for small cohorts.\n\n"
            "**Suggestion:** Broader Business Master's programs (M.S. in Finance, "
            "M.S. in Management) tend to have better data coverage. "
            "Results below use school-wide earnings as a proxy."
        ),
        "zh": (
            "💡 **MBA 薪資資料在 College Scorecard 中常不完整**。"
            "頂尖 MBA 課程（哈佛、沃頓）有時因隱私保護而資料被隱藏。\n\n"
            "**建議：** 廣義商業碩士（財務碩士、管理碩士）的資料較完整。"
            "以下結果以學校整體薪資作為代理指標。"
        ),
    },
    "26": {  # Biology & Life Sciences
        "en": (
            "💡 **Life sciences doctoral programs** (Ph.D.) are common but earnings "
            "data for Master's-level biology varies. Many M.S. biology students "
            "continue to doctoral programs, making 1-year earnings data less representative."
        ),
        "zh": (
            "💡 **生命科學碩士薪資資料**較不穩定，許多碩士生繼續攻讀博士，"
            "導致 1 年後薪資資料代表性不足。"
        ),
    },
}


def get_field_hint(cip_prefix: str, lang: str = "en") -> str | None:
    """
    Return a hint string for the given CIP 2-digit prefix, or None if no hint exists.
    """
    entry = FIELD_CREDENTIAL_HINTS.get(cip_prefix)
    if not entry:
        return None
    return entry.get(lang) or entry.get("en")
