# Usage Examples

This document demonstrates how to use `analyze_spending_trends.py` for analysis.

## Basic Usage

### 1. Prepare Data

Ensure you have the data file: `panel_2018_2023.csv`

Required columns:
```
UNITID          # Unique school identifier
year            # Year (2018-2023)
type            # Institution type ('Public' or 'Private')
fte             # Full-Time Equivalent student count
admin           # Administrative spending (USD)
instruction     # Instructional spending (USD)
research        # Research spending (USD)
state           # State appropriations (USD)
total           # Total spending (USD)
admin_pct       # Administrative spending share
instruction_pct # Instructional spending share
research_pct    # Research spending share
INSTNM          # Institution name
STABBR          # State abbreviation
```

### 2. Run Complete Analysis

```bash
python analyze_spending_trends.py
```

This executes all steps and generates output files.

### 3. View Results

**Corrected data:**
```python
import pandas as pd

# Read corrected data
df = pd.read_csv('panel_2018_2023_corrected.csv')

# View complete time series for a school
school_data = df[df['UNITID'] == 100654]  # e.g., Alabama A&M
print(school_data[['year', 'fte', 'admin_per_fte_real', 'instruction_per_fte_real']])
```

**Statistical summary:**
```python
# Read trend summary
summary = pd.read_csv('trend_analysis_summary.csv')
print(summary)
```

## Advanced Usage

### Run Specific Steps Only

```python
from analyze_spending_trends import *

# 1. Load data
df = load_and_inspect_data('panel_2018_2023.csv')

# 2. Diagnose only (no correction)
diagnosis = diagnose_fte_anomaly(df)

# 3. View diagnosis results
print(diagnosis)
```

### Use Custom Parameters

```python
# Use stricter anomaly threshold
df_corrected = correct_fte_data(df, threshold=1.5)

# Use custom CPI
custom_cpi = {
    2018: 1.00,
    2019: 1.025,  # Custom inflation rate
    2020: 1.04,
    2021: 1.09,
    2022: 1.18,
    2023: 1.22
}
df_corrected = add_inflation_adjusted_metrics(df_corrected, cpi_deflator=custom_cpi)
```

### Generate Specific Visualizations Only

```python
# Create visualization only (no re-analysis)
df = pd.read_csv('panel_2018_2023_corrected.csv')
create_comprehensive_visualization(df, output_path='custom_viz.png')
```

## Analyze Specific Subsets

### Analyze Public Universities Only

```python
df = pd.read_csv('panel_2018_2023_corrected.csv')

# Filter Public
public_df = df[df['type'] == 'Public']

# Calculate trends
public_trends = calculate_trends(public_df)
```

### Analyze by State

```python
# Analyze specific state (e.g., California)
ca_df = df[df['STABBR'] == 'CA']
ca_trends = calculate_trends(ca_df)

# Compare multiple states
states = ['CA', 'TX', 'NY', 'FL']
for state in states:
    state_df = df[df['STABBR'] == state]
    print(f"\n{state} Trends:")
    trends = calculate_trends(state_df)
```

### Analyze by Carnegie Classification

If your data includes Carnegie classification:

```python
# Group by Carnegie category
for category in df['carnegie_name'].unique():
    cat_df = df[df['carnegie_name'] == category]
    print(f"\n{category}:")
    trends = calculate_trends(cat_df)
```

## Custom Visualizations

### Create Single Metric Chart

```python
import matplotlib.pyplot as plt

df = pd.read_csv('panel_2018_2023_corrected.csv')

# Plot real instructional spending trend
yearly = df.groupby('year')['instruction_per_fte_real'].median()

plt.figure(figsize=(10, 6))
plt.plot(yearly.index, yearly.values, 'o-', linewidth=2, markersize=8)
plt.title('Real Instructional Spending per FTE (2018$)', fontsize=14, fontweight='bold')
plt.xlabel('Year')
plt.ylabel('$ per FTE (2018 dollars)')
plt.grid(True, alpha=0.3)
plt.savefig('instruction_trend.png', dpi=300, bbox_inches='tight')
```

### Create Public vs Private Comparison Chart

```python
fig, ax = plt.subplots(figsize=(12, 6))

for inst_type in ['Public', 'Private']:
    type_data = df[df['type'] == inst_type].groupby('year')['instruction_per_fte_real'].median()
    ax.plot(type_data.index, type_data.values, 'o-', linewidth=2, 
            markersize=8, label=inst_type)

ax.set_title('Real Instruction Spending: Public vs Private')
ax.set_xlabel('Year')
ax.set_ylabel('$ per FTE (2018$)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.savefig('public_vs_private.png', dpi=300, bbox_inches='tight')
```

## Export Specific Statistics

### Create Excel Report

```python
with pd.ExcelWriter('spending_analysis.xlsx') as writer:
    # Overall trends
    df.groupby('year').agg({
        'admin_pct': 'mean',
        'instruction_pct': 'mean',
        'admin_per_fte_real': 'median',
        'instruction_per_fte_real': 'median'
    }).to_excel(writer, sheet_name='Overall Trends')
    
    # Public trends
    df[df['type'] == 'Public'].groupby('year').agg({
        'admin_per_fte_real': 'median',
        'instruction_per_fte_real': 'median'
    }).to_excel(writer, sheet_name='Public Trends')
    
    # Private trends
    df[df['type'] == 'Private'].groupby('year').agg({
        'admin_per_fte_real': 'median',
        'instruction_per_fte_real': 'median'
    }).to_excel(writer, sheet_name='Private Trends')
```

## Frequently Asked Questions

### Q1: Why is FTE correction necessary?

A: 2020 FTE data shows systematic anomaly (258% increase), likely due to statistical method changes during COVID-19. Without correction, per_fte metrics are completely distorted.

### Q2: Can I skip inflation adjustment?

A: Yes, but nominal values mask real changes. Cumulative inflation 2018-2023 is 20%; without adjustment, you may misjudge spending growth.

### Q3: Why use median instead of mean?

A: Median is more robust and not affected by outliers. Higher education spending data often contains anomalies (e.g., Harvard, Stanford and other top universities).

### Q4: Can I analyze 2024 data?

A: Yes! Just:
1. Update `CPI_DEFLATOR` to add 2024 inflation rate
2. Provide data file including 2024
3. Run same script

### Q5: How to add new spending categories?

A: Modify `calculate_trends()` function, add new variable to aggregation dictionary:

```python
pct_trends = df.groupby('year').agg({
    'admin_pct': 'mean',
    'instruction_pct': 'mean',
    'your_new_category_pct': 'mean'  # Add this line
})
```

## Troubleshooting

### Error: FileNotFoundError

```
Ensure data file is in correct location:
- panel_2018_2023.csv should be in current directory
- Or modify INPUT_FILE variable in script to point to correct path
```

### Warning: SettingWithCopyWarning

```
This is a pandas warning, usually doesn't affect results.
Can add at top of script:
pd.options.mode.chained_assignment = None
```

### Memory Issues

```
If dataset is very large, you can:
1. Process in batches
2. Read CSV in chunks
3. Load only necessary columns
```

## Additional Resources

- [IPEDS Data Dictionary](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx)
- [CPI Data Source](https://www.bls.gov/cpi/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Matplotlib Tutorial](https://matplotlib.org/stable/tutorials/index.html)

## Contact Support

If you encounter issues:
1. Check README.md for complete documentation
2. Submit issue on GitHub
3. Provide error messages and data samples
