"""
Bilingual string translations (English / Traditional Chinese)
"""

T = {
    "en": {
        # --- Global ---
        "lang_label": "Language / 語言",
        "app_title": "U.S. College Value & Scholarship Platform",
        "app_subtitle": "Compare real costs, future earnings, and financial aid across 6,000+ U.S. colleges",
        "data_source": "Data: College Scorecard (U.S. Dept. of Education) + IPEDS",
        "no_data": "No data available",
        "loading": "Loading...",
        "search": "Search",
        "compare": "Compare",
        "clear": "Clear",
        "school_name": "School Name",
        "state": "State",
        "type": "Type",
        "public": "Public",
        "private_np": "Private Nonprofit",
        "private_fp": "Private For-Profit",
        "all": "All",
        "enrollment": "Enrollment",
        "admission_rate": "Admission Rate",
        "sat_avg": "Avg SAT Score",
        "completion_rate": "Graduation Rate",

        # --- Home ---
        "home_title": "Find Your Best-Value College",
        "home_desc": (
            "This platform combines **tuition costs**, **post-graduation earnings**, "
            "and **financial aid data** to help you calculate the real return on your "
            "college investment."
        ),
        "home_features": "What you can do here",
        "feat_search": "Search & filter 6,000+ U.S. colleges",
        "feat_roi": "Calculate ROI: tuition vs. 10-year earnings",
        "feat_aid": "Explore scholarships, FAFSA, and loans",
        "feat_trend": "Analyze how colleges spend your tuition",
        "home_start": "Use the sidebar to navigate",
        "quick_stats_title": "Platform Coverage",
        "stat_schools": "Colleges in Database",
        "stat_states": "States Covered",
        "stat_source": "Data Updated",

        # --- University Search ---
        "search_title": "School Profile",
        "search_desc": "Search any U.S. college to see tuition, CP value, employment outcomes, and recommended scholarships — all in one place.",
        "search_placeholder": "e.g. Boston University, UCLA, MIT",
        "filter_state": "Filter by State",
        "filter_type": "Institution Type",
        "filter_size": "Enrollment Size",
        "size_any": "Any size",
        "size_small": "Small (< 2,000)",
        "size_medium": "Medium (2,000–15,000)",
        "size_large": "Large (> 15,000)",
        "results_found": "results found",
        "tuition_instate": "In-State Tuition",
        "tuition_outstate": "Out-of-State Tuition",
        "net_price": "Avg Net Price (after aid)",
        "earnings_10yr": "Median Earnings (10 yrs after)",
        "earnings_6yr": "Median Earnings (6 yrs after)",
        "median_debt": "Median Debt at Graduation",
        "pell_rate": "Pell Grant Recipients",
        "loan_rate": "Federal Loan Recipients",
        "visit_website": "Visit School Website",
        "net_price_calc": "Net Price Calculator",
        "school_profile": "School Profile",
        "no_results": "No schools found. Try a different search term.",
        "select_school": "Click a row to see full profile",

        # --- CP Value Dashboard ---
        "cp_title": "CP Value (ROI) Dashboard",
        "cp_desc": (
            "Compare up to 5 colleges side-by-side. "
            "We calculate a **Value Score** based on earnings vs. net cost."
        ),
        "add_school": "Add a school to compare",
        "search_to_add": "Type to search schools...",
        "value_score": "Value Score",
        "value_score_help": "= 10-yr earnings ÷ avg net price. Higher is better.",
        "roi_ratio": "ROI Ratio",
        "roi_ratio_help": "How many times your annual net cost you'll earn in year 10.",
        "debt_to_income": "Debt-to-Income",
        "debt_to_income_help": "Median debt ÷ 10-yr earnings. Lower is better.",
        "cp_rank": "Value Ranking",
        "chart_tuition_vs_earn": "Net Price vs. 10-Year Earnings",
        "chart_debt_burden": "Debt Burden (Debt ÷ Annual Earnings)",
        "chart_value_score": "Value Score Comparison",
        "select_schools_prompt": "Add at least 2 schools above to compare.",
        "interpretation_title": "How to Read This",
        "interpretation_text": (
            "**Value Score** = 10-year median earnings ÷ average annual net price.  \n"
            "A score of 5 means for every $1 you pay annually, you earn $5/yr a decade later.  \n\n"
            "**Debt-to-Income** = median debt at graduation ÷ 10-year earnings.  \n"
            "Below 1.0 is generally manageable; above 1.5 is a warning sign."
        ),
        "annual_net_price": "Annual Net Price",
        "earnings_label": "10-Yr Median Earnings",

        # --- Scholarship & Aid ---
        "aid_title": "Scholarships & Financial Aid",
        "aid_desc": "A guide to federal aid, school-specific scholarships, and external funding for U.S. college students.",
        "tab_federal": "Federal Aid (FAFSA)",
        "tab_external": "External Scholarships",
        "tab_school": "School-Specific Aid",
        "tab_loans": "Loan Types Explained",

        "federal_title": "Federal Student Aid (FAFSA)",
        "federal_intro": (
            "The Free Application for Federal Student Aid (**FAFSA**) is the gateway to "
            "most U.S. financial aid. Submit it every year to remain eligible."
        ),
        "fafsa_deadline": "FAFSA Priority Deadline",
        "fafsa_deadline_val": "December 1 (for the following academic year)",
        "fafsa_url": "Apply at studentaid.gov",
        "aid_types_title": "Types of Federal Aid",
        "pell_grant_title": "Pell Grant",
        "pell_grant_desc": "Up to $7,395/year (2024–25). Does not need to be repaid. For undergrads with financial need.",
        "seog_title": "SEOG Grant",
        "seog_desc": "Up to $4,000/year. Supplemental grant for students with exceptional financial need.",
        "work_study_title": "Federal Work-Study",
        "work_study_desc": "Part-time campus jobs for students with financial need. Earnings do not count against aid.",
        "subsidized_title": "Subsidized Loans",
        "subsidized_desc": "Government pays interest while you're in school. 2024–25 rate: 6.53% (undergrad).",
        "unsubsidized_title": "Unsubsidized Loans",
        "unsubsidized_desc": "Interest accrues immediately. 6.53% undergrad / 8.08% grad (2024–25).",
        "plus_title": "PLUS Loans",
        "plus_desc": "For parents or grad students. Up to full cost of attendance. Rate: 9.08% (2024–25).",

        "external_title": "External Scholarships",
        "external_intro": "These scholarships are open regardless of which school you attend:",
        "intl_note": "Note: Many scholarships below accept international students.",

        "school_aid_title": "School-Specific Aid Finder",
        "school_aid_desc": "Search a school to find its net price calculator and financial aid office:",
        "school_aid_search": "Search school name...",
        "open_npc": "Open Net Price Calculator",
        "pell_recipients": "of students receive Pell Grants",
        "loan_recipients": "of students take federal loans",

        "loans_title": "Understanding Student Loans",
        "loan_compare_title": "Loan Comparison Table",

        # --- Programs / Major Explorer ---
        "programs_title": "Programs & Fields of Study",
        "programs_desc": "Explore earnings and debt by program at this school.",
        "programs_filter_cred": "Filter by Credential Level",
        "programs_sort": "Sort by",
        "programs_sort_earn": "Median Earnings",
        "programs_sort_debt": "Median Debt",
        "programs_sort_ratio": "Debt/Earnings Ratio",
        "programs_cred_all": "All Levels",
        "programs_no_data": "No program-level data available for this school.",
        "programs_cip": "Field of Study",
        "programs_cred": "Credential",
        "programs_earn": "Median Earnings (1yr)",
        "programs_debt": "Median Debt",
        "programs_ratio": "Debt/Earn",
        "programs_vs_title": "Credential-Level Earnings Comparison",
        "programs_vs_desc": "Fields with data at multiple credential levels (e.g. Bachelor's vs Master's).",
        "programs_loading": "Loading program data...",
        "major_title": "Major Explorer",
        "major_desc": "Compare the same field of study across multiple schools, or explore graduate vs undergraduate ROI.",
        "major_filter_field": "Select Field of Study (CIP Category)",
        "major_filter_cred": "Credential Level",
        "major_search_school": "Add a school to compare",
        "major_no_programs": "No matching programs found for the selected field.",
        "major_school_list": "Schools in Comparison",
        "major_cross_title": "Cross-School Comparison",
        "major_cross_desc": "Earnings and debt for the selected field across all added schools.",
        "major_premium_title": "Graduate Premium Calculator",
        "major_premium_desc": "Estimate how long it takes for a Master's degree to pay off vs. a Bachelor's.",
        "major_premium_extra_cost": "Extra Cost (Master's vs Bachelor's)",
        "major_premium_earn_premium": "Annual Earnings Premium",
        "major_premium_payback": "Payback Period",
        "major_premium_no_data": "Need both Bachelor's and Master's data to calculate.",
        "filter_field_of_study": "Field of Study",
        "chart_earn_debt_scatter": "Earnings vs. Debt by Program",

        # --- Spending Trends ---
        "trend_title": "How Colleges Spend Your Tuition",
        "trend_desc": (
            "Analysis of 20,603 IPEDS records across 3,700+ U.S. institutions (2018–2023). "
            "See where your tuition actually goes."
        ),
        "trend_upload": "Upload your IPEDS panel data (panel_2018_2023.csv) to see full analysis.",
        "trend_key_findings": "Key Findings",
        "trend_finding1": "Instructional spending share fell from 47.7% to 45.7% (-4.2%)",
        "trend_finding2": "Administrative spending share rose from 18.5% to 19.2% (+3.8%)",
        "trend_finding3": "Private universities spend 25.5% on admin vs. 13.5% at public schools",
        "trend_finding4": "State funding per student dropped 51.7% (2018→2023)",
        "chart_spending_share": "Average Spending Composition (2023)",
        "chart_admin_vs_inst": "Admin vs. Instruction: Public vs. Private (2023)",
        "data_not_loaded": "Upload `data/panel_2018_2023.csv` to this repo to see the full trend analysis.",
    },

    "zh": {
        # --- Global ---
        "lang_label": "Language / 語言",
        "app_title": "美國大學 CP 值與獎學金平台",
        "app_subtitle": "比較 6,000+ 所美國大學的實際學費、就業薪資與助學金資訊",
        "data_source": "資料來源：College Scorecard（美國教育部）+ IPEDS",
        "no_data": "無可用資料",
        "loading": "載入中...",
        "search": "搜尋",
        "compare": "比較",
        "clear": "清除",
        "school_name": "學校名稱",
        "state": "州別",
        "type": "類型",
        "public": "公立",
        "private_np": "私立非營利",
        "private_fp": "私立營利",
        "all": "全部",
        "enrollment": "在校人數",
        "admission_rate": "錄取率",
        "sat_avg": "SAT 平均分",
        "completion_rate": "畢業率",

        # --- Home ---
        "home_title": "找到最適合你的高 CP 值大學",
        "home_desc": (
            "本平台整合**學費成本**、**畢業後薪資**與**助學金資料**，"
            "幫你計算就讀美國大學的真實投資報酬率。"
        ),
        "home_features": "你可以在這裡做什麼",
        "feat_search": "搜尋並篩選 6,000+ 所美國大學",
        "feat_roi": "計算 ROI：學費 vs. 10 年後薪資",
        "feat_aid": "探索獎學金、FAFSA 與助學貸款",
        "feat_trend": "分析大學如何使用你的學費",
        "home_start": "使用左側選單開始瀏覽",
        "quick_stats_title": "平台覆蓋範圍",
        "stat_schools": "收錄大學數",
        "stat_states": "涵蓋州別",
        "stat_source": "資料更新",

        # --- University Search ---
        "search_title": "學校詳情",
        "search_desc": "搜尋任何美國大學，一次查看學費、CP值、就業結果與推薦獎學金。",
        "search_placeholder": "例如：Boston University, UCLA, MIT",
        "filter_state": "依州別篩選",
        "filter_type": "學校類型",
        "filter_size": "學校規模",
        "size_any": "不限",
        "size_small": "小型（< 2,000 人）",
        "size_medium": "中型（2,000–15,000 人）",
        "size_large": "大型（> 15,000 人）",
        "results_found": "筆結果",
        "tuition_instate": "州內學費",
        "tuition_outstate": "州外學費",
        "net_price": "平均實際學費（助學金後）",
        "earnings_10yr": "中位薪資（入學 10 年後）",
        "earnings_6yr": "中位薪資（入學 6 年後）",
        "median_debt": "畢業時中位學貸",
        "pell_rate": "Pell Grant 受惠比例",
        "loan_rate": "聯邦助學貸款比例",
        "visit_website": "前往學校官網",
        "net_price_calc": "淨學費計算機",
        "school_profile": "學校詳情",
        "no_results": "找不到符合的學校，請嘗試其他關鍵字。",
        "select_school": "點擊列表查看詳細資料",

        # --- CP Value Dashboard ---
        "cp_title": "CP 值（ROI）儀表板",
        "cp_desc": (
            "最多比較 5 所大學。"
            "我們根據薪資 vs. 實際學費計算 **CP 值分數**。"
        ),
        "add_school": "新增比較學校",
        "search_to_add": "輸入學校名稱搜尋...",
        "value_score": "CP 值分數",
        "value_score_help": "= 10 年後薪資 ÷ 年均實際學費。分數越高越好。",
        "roi_ratio": "投資報酬比",
        "roi_ratio_help": "第 10 年年薪是每年學費的幾倍。",
        "debt_to_income": "負債收入比",
        "debt_to_income_help": "畢業學貸 ÷ 10 年後薪資。越低越好。",
        "cp_rank": "CP 值排名",
        "chart_tuition_vs_earn": "實際學費 vs. 10 年後薪資",
        "chart_debt_burden": "學貸負擔（學貸 ÷ 年薪）",
        "chart_value_score": "CP 值分數比較",
        "select_schools_prompt": "請先新增至少 2 所學校進行比較。",
        "interpretation_title": "如何解讀數字",
        "interpretation_text": (
            "**CP 值分數** = 10 年後中位年薪 ÷ 年均實際學費。  \n"
            "分數 5 代表你每年付 1 元學費，10 年後每年賺 5 元。  \n\n"
            "**負債收入比** = 畢業學貸 ÷ 10 年後年薪。  \n"
            "低於 1.0 通常可負擔；高於 1.5 需要注意。"
        ),
        "annual_net_price": "年均實際學費",
        "earnings_label": "10 年後中位年薪",

        # --- Scholarship & Aid ---
        "aid_title": "獎學金與助學金指南",
        "aid_desc": "聯邦助學金、學校獎學金與外部獎學金的完整說明，適用於申請美國大學的學生。",
        "tab_federal": "聯邦助學金（FAFSA）",
        "tab_external": "外部獎學金",
        "tab_school": "學校專屬助學金",
        "tab_loans": "助學貸款說明",

        "federal_title": "聯邦助學金（FAFSA）",
        "federal_intro": (
            "**FAFSA**（免費聯邦助學申請）是取得美國大多數助學金的入口，"
            "每學年都必須重新申請才能保持資格。"
        ),
        "fafsa_deadline": "FAFSA 優先申請截止",
        "fafsa_deadline_val": "12 月 1 日（下一學年）",
        "fafsa_url": "於 studentaid.gov 申請",
        "aid_types_title": "聯邦助學金種類",
        "pell_grant_title": "Pell Grant（聯邦助學金）",
        "pell_grant_desc": "最高 $7,395/年（2024–25）。無需償還。適用有財務需求的大學生。",
        "seog_title": "SEOG Grant（補充教育機會助學金）",
        "seog_desc": "最高 $4,000/年。給予財務需求特別高的學生。",
        "work_study_title": "Federal Work-Study（聯邦工讀計畫）",
        "work_study_desc": "校內兼職工作，工資不計入助學金額度。",
        "subsidized_title": "補貼式助學貸款",
        "subsidized_desc": "在校期間政府負擔利息。2024–25 年利率：6.53%（大學生）。",
        "unsubsidized_title": "非補貼式助學貸款",
        "unsubsidized_desc": "貸款後立即產生利息。大學生 6.53%，研究生 8.08%（2024–25）。",
        "plus_title": "PLUS 貸款",
        "plus_desc": "適用家長或研究生。最高可借至就學全額費用。利率 9.08%（2024–25）。",

        "external_title": "外部獎學金",
        "external_intro": "以下獎學金不限申請的學校：",
        "intl_note": "注意：以下許多獎學金接受國際學生申請。",

        "school_aid_title": "學校專屬助學金查詢",
        "school_aid_desc": "搜尋學校，取得淨學費計算機與助學金辦公室連結：",
        "school_aid_search": "輸入學校名稱...",
        "open_npc": "開啟淨學費計算機",
        "pell_recipients": "的學生獲得 Pell Grant",
        "loan_recipients": "的學生使用聯邦貸款",

        "loans_title": "助學貸款完整說明",
        "loan_compare_title": "貸款比較表",

        # --- Programs / Major Explorer ---
        "programs_title": "科系與專業領域",
        "programs_desc": "探索此學校各科系的薪資與學貸資料。",
        "programs_filter_cred": "依學位層級篩選",
        "programs_sort": "排序方式",
        "programs_sort_earn": "薪資中位數",
        "programs_sort_debt": "學貸中位數",
        "programs_sort_ratio": "學貸/薪資比",
        "programs_cred_all": "全部層級",
        "programs_no_data": "此學校暫無科系層級資料。",
        "programs_cip": "科系名稱",
        "programs_cred": "學位類型",
        "programs_earn": "薪資中位數（1年後）",
        "programs_debt": "學貸中位數",
        "programs_ratio": "學貸/薪資",
        "programs_vs_title": "學位層級薪資比較",
        "programs_vs_desc": "同一科系在不同學位層級（如學士 vs 碩士）的薪資比較。",
        "programs_loading": "載入科系資料中...",
        "major_title": "專業比較器",
        "major_desc": "跨校比較同一科系，或計算碩士 vs 學士的投資回報差異。",
        "major_filter_field": "選擇科系大類（CIP）",
        "major_filter_cred": "學位層級",
        "major_search_school": "新增學校進行比較",
        "major_no_programs": "所選科系無比對資料。",
        "major_school_list": "比較中的學校",
        "major_cross_title": "跨校比較",
        "major_cross_desc": "各校所選科系的薪資與學貸比較。",
        "major_premium_title": "碩士溢價計算機",
        "major_premium_desc": "計算讀碩士 vs 只有學士學位，多久才能回本。",
        "major_premium_extra_cost": "額外成本（碩士 vs 學士）",
        "major_premium_earn_premium": "年薪溢價",
        "major_premium_payback": "回本年數",
        "major_premium_no_data": "需要同時有學士與碩士資料才能計算。",
        "filter_field_of_study": "科系領域",
        "chart_earn_debt_scatter": "各科系薪資 vs 學貸散佈圖",

        # --- Spending Trends ---
        "trend_title": "學費去哪了？大學支出分析",
        "trend_desc": (
            "分析 3,700+ 所美國大學的 20,603 筆 IPEDS 資料（2018–2023），"
            "看清楚你的學費實際用在哪裡。"
        ),
        "trend_upload": "請上傳 IPEDS 面板資料（panel_2018_2023.csv）以查看完整分析。",
        "trend_key_findings": "關鍵發現",
        "trend_finding1": "教學支出佔比從 47.7% 降至 45.7%（-4.2%）",
        "trend_finding2": "行政支出佔比從 18.5% 升至 19.2%（+3.8%）",
        "trend_finding3": "私立大學行政支出佔 25.5%，公立僅 13.5%",
        "trend_finding4": "州政府對公立大學的每生補助下降 51.7%（2018→2023）",
        "chart_spending_share": "平均支出組成（2023年）",
        "chart_admin_vs_inst": "行政 vs. 教學：公立 vs. 私立（2023年）",
        "data_not_loaded": "請將 `data/panel_2018_2023.csv` 放入 repo 以查看完整趨勢分析。",
    }
}

US_STATES = [
    "All", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC", "PR"
]


def t(key: str, lang: str = "en") -> str:
    """Return translated string for the given key and language."""
    return T.get(lang, T["en"]).get(key, key)
