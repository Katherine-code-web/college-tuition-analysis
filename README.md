# U.S. Higher Education Spending Trends Analysis (2018-2023)

Comprehensive time-series analysis of higher education spending, including FTE data correction, inflation adjustment, statistical testing, and visualization.

## 📊 Project Overview

This project analyzes spending trends at U.S. higher education institutions from 2018-2023, focusing on:
- Changes in administrative vs. instructional spending structure
- Real spending trends after inflation adjustment
- Differences between Public and Private universities
- Impact of COVID-19 on higher education finances

## 🔍 Key Findings

### Core Results (2018→2023)

**Spending Structure Changes:**
- Administrative spending share: 18.5% → 19.2% (+3.8%, p=0.0018**)
- Instructional spending share: 47.7% → 45.7% (-4.2%, p=0.0074**)

**Real Per-FTE Spending (Inflation-Adjusted):**
- Admin per FTE: -9.0% (p=0.0185*)
- **Instruction per FTE: -12.6% (p=0.0033**)** ⚠️
- Total per FTE: -9.3% (p=0.0037**)

**Public vs Private Differences:**
- Private instructional spending real decline: -13.7% (Public only -6.7%)
- Private administrative share is 1.9× that of Public (25.5% vs 13.5%)

## 📁 File Structure

```
.
├── analyze_spending_trends.py    # Main analysis script
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── panel_2018_2023.csv           # Raw data (prepare yourself)
│
└── outputs/                       # Output folder (auto-generated)
    ├── panel_2018_2023_corrected.csv       # Corrected data
    ├── trend_analysis_summary.csv          # Statistical summary
    └── trend_analysis_comprehensive.png    # Visualization
```

## 🚀 Quick Start

### System Requirements

- Python 3.8+
- pandas
- numpy
- matplotlib
- seaborn
- scipy

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Analysis

```bash
python analyze_spending_trends.py
```

### Expected Output

The script will generate:
1. **Corrected Dataset** (`panel_2018_2023_corrected.csv`)
   - FTE data corrected
   - Includes real spending metrics
   - Ready for further analysis

2. **Statistical Summary** (`trend_analysis_summary.csv`)
   - Annual trend statistics
   - Key metric changes

3. **Comprehensive Visualization** (`trend_analysis_comprehensive.png`)
   - 12 subplots
   - Complete trend display

## 📖 Code Documentation

### Core Function Modules

#### 1. Data Loading & Inspection (`load_and_inspect_data`)
```python
# Load raw data and perform basic checks
df = load_and_inspect_data('panel_2018_2023.csv')
```
- Read CSV file
- Check data integrity
- Report basic statistics

#### 2. FTE Anomaly Diagnosis (`diagnose_fte_anomaly`)
```python
# Diagnose 2020 FTE data anomaly
diagnosis = diagnose_fte_anomaly(df)
```
**Background:**
- 2020 FTE data shows abnormal spike of +258%
- Affects 92.2% of schools
- Likely due to statistical method changes during COVID-19

**Diagnostic Method:**
- Calculate year-over-year change rates
- Identify anomalous patterns
- Quantify affected scope

#### 3. FTE Data Correction (`correct_fte_data`)
```python
# Correct 2020-2023 FTE data
df_corrected = correct_fte_data(df, threshold=2.0)
```
**Correction Strategy:**
1. Identify anomalous schools (2020/2019 > 2×)
2. Calculate normal 2018-2019 growth rate
3. Extrapolate this rate to 2020-2023
4. Recalculate per_fte metrics

**Mathematical Formula:**
```
growth_rate = (FTE_2019 - FTE_2018) / FTE_2018
FTE_2020_corrected = FTE_2019 × (1 + growth_rate)
FTE_2021_corrected = FTE_2020_corrected × (1 + growth_rate)
...
```

#### 4. Inflation Adjustment (`add_inflation_adjusted_metrics`)
```python
# Add real metrics (2018 dollars)
df_corrected = add_inflation_adjusted_metrics(df_corrected)
```
**CPI Deflator:**
- 2018: 1.00 (base year)
- 2019: 1.02 (+2%)
- 2020: 1.03 (+1%)
- 2021: 1.08 (+5%)
- 2022: 1.16 (+8%)
- 2023: 1.20 (+4%)

**Calculation Formula:**
```
real_value = nominal_value / CPI_deflator[year]
```

#### 5. Trend Analysis (`calculate_trends`)
```python
# Perform comprehensive trend analysis
trends = calculate_trends(df_corrected)
```
**Includes:**
- Spending share trends (admin_pct, instruction_pct)
- Nominal per-FTE spending trends
- Real per-FTE spending trends
- Public vs Private group analysis
- Linear regression significance tests

**Statistical Method:**
```python
slope, intercept, r_value, p_value, std_err = stats.linregress(years, values)
# slope: annual rate of change
# r_value²: trend explanatory power
# p_value: significance level
```

#### 6. Visualization (`create_comprehensive_visualization`)
```python
# Create comprehensive visualization with 12 subplots
create_comprehensive_visualization(df_corrected)
```
**Chart Layout (4 rows × 3 columns):**
- Row 1: Spending share trends
- Row 2: Nominal per-FTE spending
- Row 3: Real per-FTE spending
- Row 4: Real absolute spending + change summary

## 🔧 Customization

### Modify CPI Deflator

To use different inflation data:

```python
# Modify in analyze_spending_trends.py
CPI_DEFLATOR = {
    2018: 1.00,
    2019: 1.02,  # Custom value
    2020: 1.03,
    # ...
}
```

### Adjust Anomaly Threshold

Correct more or fewer FTE anomalies:

```python
# Default threshold is 2.0 (i.e., >100% growth)
df_corrected = correct_fte_data(df, threshold=1.5)  # Stricter
df_corrected = correct_fte_data(df, threshold=3.0)  # More lenient
```

### Change Output Paths

```python
# Modify in configuration section at top of script
OUTPUT_CORRECTED_DATA = 'your_path/corrected_data.csv'
OUTPUT_VISUALIZATION = 'your_path/visualization.png'
```

## 📊 Data Source

**IPEDS (Integrated Postsecondary Education Data System)**
- Source: U.S. Department of Education
- URL: https://nces.ed.gov/ipeds/
- Coverage: All federally-funded higher education institutions
- Period: 2018-2023 academic years

**Key Variables:**
- `admin`: Administrative and general institutional spending
- `instruction`: Instructional spending (faculty salaries, course costs)
- `research`: Research spending
- `fte`: Full-Time Equivalent student count
- `type`: Public/Private

## 🧪 Methodology

### Statistical Tests

**Linear Regression Trend Tests:**
- Null hypothesis (H₀): No trend (slope = 0)
- Alternative hypothesis (H₁): Trend exists (slope ≠ 0)
- Significance level: α = 0.05

**Significance Standards:**
- `***`: p < 0.001 (extremely significant)
- `**`: p < 0.01 (very significant)
- `*`: p < 0.05 (significant)
- `NS`: p ≥ 0.05 (not significant)

### Robustness Measures

**Using Medians Instead of Means:**
- Avoid influence of outliers
- More robust estimates

**Group Validation:**
- Separate analysis for Public vs Private
- Confirm trend consistency

**Multi-Metric Cross-Validation:**
- Shares + absolute values + per-capita values
- Triple verification ensures reliable conclusions

## ⚠️ Research Limitations

1. **Causality**
   - This is descriptive analysis
   - Cannot establish causal relationships
   - Reports correlations and trends only

2. **Data Quality**
   - FTE data requires correction
   - Relies on institutional self-reporting
   - Potential measurement errors

3. **External Validity**
   - Results apply to U.S. higher education only
   - Situations may differ in other countries

4. **Unobserved Variables**
   - Lacks faculty data
   - Lacks student outcome data
   - Cannot assess educational quality changes

## 📝 Citation

If you use this analysis in research or projects, please cite:

```
YUN TING SU. (2026). U.S. Higher Education Spending Trends Analysis (2018-2023).
GitHub repository: https://github.com/your-username/your-repo
```

## 🤝 Contributing

Contributions welcome! Please follow these steps:

1. Fork this project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📧 Contact

For questions or suggestions, please contact through:

- GitHub Issues: [Create issue here]
- Email: kt0704@bu.edu

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- U.S. Department of Education IPEDS for data provision
- U.S. Bureau of Labor Statistics for CPI data
- Anthropic Claude for analysis and documentation assistance

---

**Last Updated:** February 4, 2026  
**Version:** 1.0.0  
**Status:** Stable Release
