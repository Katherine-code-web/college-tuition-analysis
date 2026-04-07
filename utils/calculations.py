"""
ROI / CP Value calculation functions
"""

import pandas as pd
import numpy as np


def compute_value_score(earnings_10yr, net_price, completion_rate=None) -> float | None:
    """
    Value Score = 10-year median earnings / annual net price.

    Optionally weighted by completion rate (probability-adjusted ROI).
    Higher is better.

    Returns None if required inputs are missing.
    """
    if not earnings_10yr or not net_price or net_price == 0:
        return None
    score = earnings_10yr / net_price
    if completion_rate and completion_rate > 0:
        score *= completion_rate  # Penalizes schools where most students don't finish
    return round(score, 2)


def compute_debt_to_income(median_debt, earnings_10yr) -> float | None:
    """
    Debt-to-Income = median debt at graduation / 10-year earnings.

    Below 1.0 is generally manageable. Above 1.5 is a warning sign.
    Returns None if inputs are missing.
    """
    if not median_debt or not earnings_10yr or earnings_10yr == 0:
        return None
    return round(median_debt / earnings_10yr, 2)


def compute_payback_years(net_price, earnings_10yr, years=4) -> float | None:
    """
    Estimate how many years of post-grad earnings cover total tuition cost.

    payback_years = (net_price × years) / earnings_10yr
    """
    if not net_price or not earnings_10yr or earnings_10yr == 0:
        return None
    total_cost = net_price * years
    return round(total_cost / earnings_10yr, 1)


def enrich_df(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed ROI metrics to a school DataFrame."""
    df = df.copy()
    df["value_score"] = df.apply(
        lambda r: compute_value_score(r["earnings_10yr"], r["net_price"], r["completion_rate"]),
        axis=1,
    )
    df["debt_to_income"] = df.apply(
        lambda r: compute_debt_to_income(r["median_debt"], r["earnings_10yr"]),
        axis=1,
    )
    df["payback_years"] = df.apply(
        lambda r: compute_payback_years(r["net_price"], r["earnings_10yr"]),
        axis=1,
    )
    return df


def score_label(score: float | None, lang: str = "en") -> str:
    """Return a human-readable label for a value score."""
    if score is None:
        return "N/A"
    labels = {
        "en": {(0, 2): "Low", (2, 4): "Fair", (4, 6): "Good", (6, 999): "Excellent"},
        "zh": {(0, 2): "偏低", (2, 4): "普通", (4, 6): "良好", (6, 999): "優秀"},
    }
    for (lo, hi), label in labels.get(lang, labels["en"]).items():
        if lo <= score < hi:
            return label
    return "N/A"


# ── Animal mascot system ──────────────────────────────────────────────────────
CP_ANIMALS = [
    {
        "min": 6, "max": 999,
        "emoji": "🐯",
        "name_en": "Tiger", "name_zh": "老虎",
        "title_en": "TOP PREDATOR", "title_zh": "頂尖掠食者",
        "desc_en": "Exceptional ROI. This school earns its keep — and then some.",
        "desc_zh": "超高 CP 值！就讀這所學校，薪資完全值回票價。",
        "color": "#FF8C42",
        "bg": "#FFF3E4",
        "art": """
  /\\_/\\
 ( >ω< )
  > 🐯 <
""",
    },
    {
        "min": 4, "max": 6,
        "emoji": "🦊",
        "name_en": "Fox", "name_zh": "狐狸",
        "title_en": "SMART HUSTLER", "title_zh": "聰明划算",
        "desc_en": "Solid ROI. A clever pick with strong earning potential.",
        "desc_zh": "不錯的 CP 值，聰明的選擇，薪資潛力紮實。",
        "color": "#E8503A",
        "bg": "#FFEEE8",
        "art": """
  /\\_/\\
 ( ^ᵕ^ )
  > 🦊 <
""",
    },
    {
        "min": 2, "max": 4,
        "emoji": "🐨",
        "name_en": "Koala", "name_zh": "無尾熊",
        "title_en": "CHILL & STEADY", "title_zh": "還算可以",
        "desc_en": "Decent ROI. Comfortable but room to grow.",
        "desc_zh": "CP 值普通，還算舒適，但有進步空間。",
        "color": "#7B8FA1",
        "bg": "#EEF2F5",
        "art": """
  /\\_/\\
 ( ᵕ‿ᵕ)
  > 🐨 <
""",
    },
    {
        "min": 0, "max": 2,
        "emoji": "🦥",
        "name_en": "Sloth", "name_zh": "樹懶",
        "title_en": "TAKE IT SLOW", "title_zh": "慢慢來吧",
        "desc_en": "Low ROI. Consider aid options or compare alternatives.",
        "desc_zh": "CP 值偏低，建議多申請助學金或比較其他選項。",
        "color": "#8B6F47",
        "bg": "#F5EDE0",
        "art": """
  /\\_/\\
 ( -ω-)
  > 🦥 <
""",
    },
]

NO_DATA_ANIMAL = {
    "emoji": "🐾",
    "name_en": "Mystery", "name_zh": "神秘動物",
    "title_en": "DATA UNKNOWN", "title_zh": "資料不足",
    "desc_en": "Not enough data to calculate ROI. Check the school's net price calculator.",
    "desc_zh": "資料不足，無法計算 CP 值。請至學校官網查詢淨學費計算機。",
    "color": "#999",
    "bg": "#F5F5F5",
}


def get_cp_animal(score: float | None) -> dict:
    """Return the animal mascot dict for a given CP value score."""
    if score is None:
        return NO_DATA_ANIMAL
    for animal in CP_ANIMALS:
        if animal["min"] <= score < animal["max"]:
            return animal
    return NO_DATA_ANIMAL


def cp_animal_badge_html(score: float | None, lang: str = "en") -> str:
    """
    Return a Zootopia-style HTML badge showing the animal mascot for this CP score.
    Designed to be injected via st.markdown(..., unsafe_allow_html=True).
    """
    animal = get_cp_animal(score)
    name = animal["name_en"] if lang == "en" else animal["name_zh"]
    title = animal["title_en"] if lang == "en" else animal["title_zh"]
    desc = animal["desc_en"] if lang == "en" else animal["desc_zh"]
    score_str = f"{score:.2f}" if score is not None else "N/A"
    label = score_label(score, lang)

    return (
        f'<div style="background:{animal["bg"]};border:3px solid #1A1A1A;border-radius:16px;'
        f'box-shadow:5px 5px 0px #1A1A1A;padding:20px 24px;display:flex;align-items:center;'
        f'gap:20px;margin:16px 0;font-family:Nunito,sans-serif;">'
        f'<div style="font-size:4.5rem;line-height:1;flex-shrink:0;">{animal["emoji"]}</div>'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="display:inline-block;background:{animal["color"]};color:white;'
        f'font-family:Fredoka One,cursive;font-size:0.75rem;letter-spacing:2px;'
        f'padding:3px 10px;border-radius:4px;border:2px solid #1A1A1A;margin-bottom:6px;">'
        f'{title}</div>'
        f'<div style="font-family:Fredoka One,cursive;font-size:1.5rem;color:#1A1A1A;line-height:1.2;">'
        f'{animal["emoji"]} {name} &nbsp;'
        f'<span style="background:white;border:2.5px solid #1A1A1A;border-radius:8px;'
        f'padding:2px 10px;font-size:1.3rem;color:{animal["color"]};">'
        f'{score_str} <span style="font-size:0.9rem;color:#555;">({label})</span></span></div>'
        f'<div style="font-size:0.88rem;color:#444;font-weight:700;margin-top:6px;line-height:1.4;">'
        f'{desc}</div>'
        f'</div></div>'
    )


def debt_label(ratio: float | None, lang: str = "en") -> str:
    """Return a traffic-light label for debt-to-income ratio."""
    if ratio is None:
        return "N/A"
    if lang == "zh":
        if ratio < 0.5:
            return "🟢 低負擔"
        elif ratio < 1.0:
            return "🟡 可負擔"
        elif ratio < 1.5:
            return "🟠 注意"
        else:
            return "🔴 高負擔"
    else:
        if ratio < 0.5:
            return "🟢 Low"
        elif ratio < 1.0:
            return "🟡 Manageable"
        elif ratio < 1.5:
            return "🟠 Caution"
        else:
            return "🔴 High Risk"
