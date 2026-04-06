# U.S. Higher Education Spending Analysis (2018–2023)

A data-driven investigation into why U.S. college costs keep rising, analyzing 20,603 records across 3,700+ institutions using IPEDS data.

---

## Business Problem

Students pay more but get less — where does the money go?

U.S. college tuition has risen steadily while state funding collapsed during COVID-19. This project quantifies exactly how university budgets shifted between 2018 and 2023, separating the signal (structural administrative bloat) from the noise (inflation, enrollment swings).

---

## Key Findings

| Metric | 2018 | 2023 | Change | Significance |
|--------|------|------|--------|--------------|
| Admin spending share | 18.5% | 19.2% | +3.8% | p=0.0018 ** |
| Instruction spending share | 47.7% | 45.7% | -4.2% | p=0.0074 ** |
| Real admin per FTE | baseline | -9.0% | | p=0.0185 * |
| Real instruction per FTE | baseline | -12.6% | | p=0.0033 ** |

**Private vs. Public (2023):** Private universities spend 25.5% on administration vs. 13.5% at public institutions — a 1.9x gap — yet allocate less to instruction (42.3% vs. 48.7%).

**State disinvestment:** Average state funding per public-university student fell 51.7% between 2018 and 2023, shifting costs from governments to students.

**Bottom line:** Universities cut teaching investment before cutting administrative overhead when budgets tightened. Students bear higher tuition while receiving proportionally less instruction.

---

## Tech Stack

- **Python**: Pandas, NumPy, SciPy, Matplotlib, Seaborn
- **SQL**: SQLite (window functions, CTEs, NTILE segmentation)
- **Visualization**: Matplotlib (12-panel dashboard), Tableau
- **Data**: IPEDS (U.S. Dept. of Education)

---

## Project Structure

```
college-tuition-analysis/
├── analyze_spending_trends.py          # Main Python analysis script
├── sql_data_pipeline.py                # SQL analytics pipeline (SQLite)
├── requirements.txt                    # Python dependencies
│
├── data/
│   └── panel_2018_2023.csv             # IPEDS panel data (place here before running)
│
├── queries/
│   ├── 01_state_spending_gap_ranking.sql
│   ├── 02_yoy_spending_changes.sql
│   └── 03_institution_tier_analysis.sql
│
├── outputs/                            # Auto-generated (gitignored CSVs)
│   ├── panel_2018_2023_corrected.csv
│   ├── trend_analysis_summary.csv
│   ├── trend_analysis_comprehensive.png
│   ├── query1_state_spending_gap.csv
│   ├── query2_yoy_spending_changes.csv
│   └── query3_institution_tier_analysis.csv
│
├── reports/
│   └── final_report.md                 # Full written analysis
│
├── visualizations/                     # Pre-generated charts
│
└── docs/
    ├── USAGE_EXAMPLES_EN.md
    └── COLAB_GUIDE.md
```

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Place data file

Download the IPEDS panel data and place it at `data/panel_2018_2023.csv`.

### 3. Run the Python analysis

```bash
python analyze_spending_trends.py
```

Outputs are written to `outputs/`:
- `panel_2018_2023_corrected.csv` — FTE-corrected, inflation-adjusted dataset
- `trend_analysis_summary.csv` — annual trend statistics
- `trend_analysis_comprehensive.png` — 12-panel visualization

### 4. Run the SQL pipeline

```bash
python sql_data_pipeline.py
```

Outputs are written to `outputs/`:
- `query1_state_spending_gap.csv` — state-level admin vs. instruction gap ranking
- `query2_yoy_spending_changes.csv` — year-over-year changes per institution
- `query3_institution_tier_analysis.csv` — institution tier segmentation

### 5. Run in Google Colab

See [docs/COLAB_GUIDE.md](docs/COLAB_GUIDE.md) for step-by-step Colab instructions.

---

## Methodology

### Data Processing

- **FTE correction**: 2020 FTE data shows a system-wide +258% spike (affecting 92.2% of institutions), likely from COVID-era methodology changes. Anomalous values are replaced by extrapolating each institution's 2018–2019 growth rate forward.
- **Inflation adjustment**: All nominal spending converted to constant 2018 dollars using BLS CPI deflators (cumulative inflation 2018–2023: +20%).
- **Robustness**: Medians used throughout to resist outlier distortion from elite research universities.

### Statistical Methods

| Test | Use case |
|------|----------|
| Linear regression | Time-trend significance (slope ≠ 0) |
| Paired t-test | Same-institution 2018 vs. 2023 comparison |
| Independent t-test | Public vs. private differences |
| Cohen's d | Effect size for practical significance |

Significance thresholds: `***` p < 0.001, `**` p < 0.01, `*` p < 0.05.

### SQL Queries

1. **State spending gap ranking** — CTE-based 2018→2023 admin vs. instruction delta, ranked with `RANK()` window function
2. **Year-over-year changes** — `LAG()` and `FIRST_VALUE()` window functions for per-institution temporal comparison
3. **Institution tier segmentation** — `NTILE(3)` dynamic percentile cutoffs to classify institutions as high/medium/low admin spenders, then aggregate by tier

---

## Data Source

**IPEDS (Integrated Postsecondary Education Data System)**
- Provider: U.S. Department of Education, National Center for Education Statistics
- URL: https://nces.ed.gov/ipeds/
- Surveys: Finance (F1A/F2), Institutional Characteristics (HD), Enrollment (EFFY)
- Coverage: 2018–2023 academic years, all federally-funded institutions

**Key variables:**
- `admin` — Administrative and general institutional support spending
- `instruction` — Instructional spending (faculty salaries, course costs)
- `research` — Research spending
- `fte` — Full-Time Equivalent student enrollment
- `type` — Public (GASB) or Private Nonprofit (FASB)
- `state` — State appropriations (public institutions only)

---

## Research Limitations

1. **Descriptive only** — Trend correlations are identified; causal relationships require further study.
2. **Self-reported data** — Relies on institutional IPEDS submissions; measurement error is possible.
3. **Missing variables** — Federal funding, endowment income, and faculty counts are not included.
4. **U.S. scope** — Findings apply to U.S. higher education; international comparison is out of scope.

---

## Citation

```
Yun-Ting Su. (2026). U.S. Higher Education Spending Trends Analysis (2018-2023).
GitHub: https://github.com/Katherine-code-web/college-tuition-analysis
```

---

## Author

**Yun-Ting Su** | Boston University MSBA
[kt0704@bu.edu](mailto:kt0704@bu.edu) | [linkedin.com/in/yun-ting-su-867b70364](https://linkedin.com/in/yun-ting-su-867b70364)

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

**Data source:** U.S. Department of Education IPEDS | CPI data: U.S. Bureau of Labor Statistics
