"""
U.S. Higher Education Spending Trends Analysis (2018-2023)
===========================================================

This script performs comprehensive time-series analysis of higher education spending,
including:
1. FTE Data Correction (handling 2020-2023 anomalies)
2. Inflation Adjustment (CPI deflator)
3. Spending Share Trend Analysis
4. Nominal vs. Real Spending Comparison
5. Public vs. Private Institution Comparison
6. Statistical Significance Testing

Author: Yun-Ting Su
Date: 2026-02-04
Data Source: IPEDS (Integrated Postsecondary Education Data System)
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# Configuration
# ============================================================================

# Input file path
INPUT_FILE = 'data/panel_2018_2023.csv'

# Output directory
OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Output file paths
OUTPUT_CORRECTED_DATA = os.path.join(OUTPUT_DIR, 'panel_2018_2023_corrected.csv')
OUTPUT_SUMMARY_STATS = os.path.join(OUTPUT_DIR, 'trend_analysis_summary.csv')
OUTPUT_VISUALIZATION = os.path.join(OUTPUT_DIR, 'trend_analysis_comprehensive.png')

# CPI deflator (base year 2018 = 1.00)
# Data source: U.S. Bureau of Labor Statistics
CPI_DEFLATOR = {
    2018: 1.00,  # Base year
    2019: 1.02,  # +2%
    2020: 1.03,  # +1%
    2021: 1.08,  # +5%
    2022: 1.16,  # +8%
    2023: 1.20   # +4%
}

# FTE anomaly threshold (2020/2019 ratio above this value is flagged as anomalous)
FTE_ANOMALY_THRESHOLD = 2.0

# Statistical significance level
ALPHA_LEVEL = 0.05

# ============================================================================
# Part 1: Data Loading and Initial Inspection
# ============================================================================

def load_and_inspect_data(filepath):
    """
    Load raw data and perform initial quality checks.

    Parameters
    ----------
    filepath : str
        Path to the data file.

    Returns
    -------
    df : pandas.DataFrame
        Loaded dataframe.
    """
    print("=" * 80)
    print("STEP 1: Loading Data")
    print("=" * 80)

    # Read CSV
    df = pd.read_csv(filepath)

    # Basic info
    print(f"\nData dimensions: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"Time range: {df['year'].min()} - {df['year'].max()}")
    print(f"Number of institutions: {df['UNITID'].nunique()}")

    # Annual distribution
    print("\nObservations by year:")
    print(df['year'].value_counts().sort_index())

    # Distribution by institution type
    print("\nDistribution by institution type:")
    print(df['type'].value_counts())

    # Missing value check
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print("\nMissing value statistics (columns with missing values only):")
        print(missing[missing > 0])

    return df


# ============================================================================
# Part 2: FTE Data Correction
# ============================================================================

def diagnose_fte_anomaly(df):
    """
    Diagnose the FTE data anomaly.

    Background: 2020 FTE data shows a systematic spike (+258%), likely caused by
    changes in statistical methodology or remote-learning student counting during
    COVID-19.

    Parameters
    ----------
    df : pandas.DataFrame
        Raw data.

    Returns
    -------
    diagnosis : dict
        Diagnostic statistics by year.
    """
    print("\n" + "=" * 80)
    print("STEP 2: FTE Data Anomaly Diagnosis")
    print("=" * 80)

    # Compute year-over-year change rates
    df_sorted = df.sort_values(['UNITID', 'year']).copy()
    df_sorted['fte_change'] = df_sorted.groupby('UNITID')['fte'].pct_change(fill_method=None)

    diagnosis = {}

    # Check anomaly rates by year
    for year in range(2019, 2024):
        if year in df['year'].values:
            changes = df_sorted[df_sorted['year'] == year]['fte_change']
            n_anomaly = (changes.abs() > 1.0).sum()  # >100% change flagged as anomalous
            n_total = changes.notna().sum()

            diagnosis[year] = {
                'anomaly_count': n_anomaly,
                'total_count': n_total,
                'anomaly_pct': n_anomaly / n_total * 100 if n_total > 0 else 0,
                'mean_change': changes.mean() * 100,
                'median_change': changes.median() * 100
            }

            print(f"\n{year-1} -> {year}:")
            print(f"  Anomalous institutions: {n_anomaly} / {n_total} ({diagnosis[year]['anomaly_pct']:.1f}%)")
            print(f"  Mean change rate: {diagnosis[year]['mean_change']:.1f}%")
            print(f"  Median change rate: {diagnosis[year]['median_change']:.1f}%")

    # Highlight the 2020 anomaly
    if 2020 in diagnosis:
        print("\n" + "!" * 80)
        print(f"WARNING: Severe anomaly detected in 2020 — "
              f"{diagnosis[2020]['anomaly_pct']:.1f}% of institutions show abnormal FTE growth")
        print(f"   Mean growth rate: {diagnosis[2020]['mean_change']:.1f}%")
        print("!" * 80)

    return diagnosis


def correct_fte_data(df, threshold=FTE_ANOMALY_THRESHOLD):
    """
    Correct anomalous FTE data.

    Strategy: For institutions where 2020 FTE spiked above the threshold
    (2020/2019 > threshold), extrapolate 2020-2023 FTE values using the
    normal 2018-2019 growth rate.

    Parameters
    ----------
    df : pandas.DataFrame
        Raw data.
    threshold : float
        Anomaly threshold (default 2.0, meaning >100% growth is anomalous).

    Returns
    -------
    df_corrected : pandas.DataFrame
        Data with corrected FTE values.
    """
    print("\n" + "=" * 80)
    print("STEP 3: FTE Data Correction")
    print("=" * 80)

    df_corrected = df.copy()

    # Create pivot table for easier manipulation
    fte_pivot = df.pivot(index='UNITID', columns='year', values='fte')

    # Identify institutions needing correction
    if 2019 in fte_pivot.columns and 2020 in fte_pivot.columns:
        needs_correction = (
            (fte_pivot[2020] / fte_pivot[2019] > threshold) &
            fte_pivot[2020].notna() &
            fte_pivot[2019].notna()
        )
        n_corrected = needs_correction.sum()
        print(f"\nInstitutions requiring correction: {n_corrected}")

        # Apply correction for each flagged institution
        for unitid in fte_pivot[needs_correction].index:
            # Compute 2018-2019 baseline growth rate
            fte_2018 = fte_pivot.loc[unitid, 2018] if 2018 in fte_pivot.columns else np.nan
            fte_2019 = fte_pivot.loc[unitid, 2019]

            if pd.notna(fte_2018) and pd.notna(fte_2019):
                growth_rate = (fte_2019 - fte_2018) / fte_2018
            else:
                # If no 2018 data, assume zero growth
                growth_rate = 0.0

            # Extrapolate 2020-2023
            fte_2019_value = fte_2019
            for year in [2020, 2021, 2022, 2023]:
                if year in df['year'].values:
                    fte_corrected = fte_2019_value * ((1 + growth_rate) ** (year - 2019))
                    df_corrected.loc[
                        (df_corrected['UNITID'] == unitid) &
                        (df_corrected['year'] == year),
                        'fte'
                    ] = fte_corrected

        print(f"Correction complete — {n_corrected} institutions corrected for 2020-2023")

    return df_corrected


def recalculate_per_fte_metrics(df):
    """
    Recalculate per-FTE spending metrics after FTE correction.

    Parameters
    ----------
    df : pandas.DataFrame
        Data with corrected FTE values.

    Returns
    -------
    df : pandas.DataFrame
        Data with updated per-FTE metrics.
    """
    print("\nRecalculating per-FTE metrics...")

    df['admin_per_fte'] = df['admin'] / df['fte']
    df['instruction_per_fte'] = df['instruction'] / df['fte']
    df['state_per_fte'] = df['state'] / df['fte']
    df['total_per_fte'] = df['total'] / df['fte']

    # Handle infinite values and NaN
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    print("Per-FTE metrics updated.")

    return df


# ============================================================================
# Part 3: Inflation Adjustment
# ============================================================================

def add_inflation_adjusted_metrics(df, cpi_deflator=CPI_DEFLATOR):
    """
    Add inflation-adjusted (real) spending metrics.

    Converts all nominal dollar amounts to constant 2018 dollars, enabling
    meaningful comparison of real purchasing power across years.

    Parameters
    ----------
    df : pandas.DataFrame
        Data with nominal spending values.
    cpi_deflator : dict
        CPI deflator by year (base year 2018 = 1.00).

    Returns
    -------
    df : pandas.DataFrame
        Data with real spending metrics appended.
    """
    print("\n" + "=" * 80)
    print("STEP 4: Inflation Adjustment")
    print("=" * 80)

    print("\nCPI Deflator (2018 = 1.00):")
    for year, deflator in sorted(cpi_deflator.items()):
        cumulative_inflation = (deflator - 1.0) * 100
        print(f"  {year}: {deflator:.2f} (Cumulative inflation: {cumulative_inflation:+.1f}%)")

    # Real institutional-level spending
    df['admin_real'] = df.apply(lambda x: x['admin'] / cpi_deflator[x['year']], axis=1)
    df['instruction_real'] = df.apply(lambda x: x['instruction'] / cpi_deflator[x['year']], axis=1)
    df['total_real'] = df.apply(lambda x: x['total'] / cpi_deflator[x['year']], axis=1)

    # Real per-FTE spending
    df['admin_per_fte_real'] = df.apply(lambda x: x['admin_per_fte'] / cpi_deflator[x['year']], axis=1)
    df['instruction_per_fte_real'] = df.apply(lambda x: x['instruction_per_fte'] / cpi_deflator[x['year']], axis=1)
    df['total_per_fte_real'] = df.apply(lambda x: x['total_per_fte'] / cpi_deflator[x['year']], axis=1)

    print("\nReal metrics added:")
    print("  - *_real: Institution-level real spending (2018 dollars)")
    print("  - *_per_fte_real: Per-FTE real spending (2018 dollars)")

    return df


# ============================================================================
# Part 4: Trend Analysis
# ============================================================================

def calculate_trends(df):
    """
    Compute comprehensive trend statistics.

    Includes:
    1. Spending Share Trends
    2. Nominal Per-FTE Spending Trends
    3. Real Per-FTE Spending Trends
    4. Public vs. Private Grouped Trends

    Parameters
    ----------
    df : pandas.DataFrame
        Fully processed data.

    Returns
    -------
    results : dict
        Dictionary containing all trend analysis results.
    """
    print("\n" + "=" * 80)
    print("STEP 5: Trend Analysis")
    print("=" * 80)

    results = {}

    # ========================================================================
    # 5.1 Spending Share Trends
    # ========================================================================
    print("\n[A. Spending Share Trends]")

    pct_trends = df.groupby('year').agg({
        'admin_pct': 'mean',
        'instruction_pct': 'mean',
        'research_pct': 'mean'
    }).round(4)

    print("\nAnnual average shares:")
    print(pct_trends)

    # 2018 -> 2023 change
    if 2018 in pct_trends.index and 2023 in pct_trends.index:
        pct_change = (
            (pct_trends.loc[2023] - pct_trends.loc[2018]) /
            pct_trends.loc[2018] * 100
        ).round(1)
        print("\n2018 -> 2023 change (%):")
        print(pct_change)

    # Trend significance tests
    print("\nTrend Significance Tests (Linear Regression):")
    pct_significance = {}
    for var in ['admin_pct', 'instruction_pct', 'research_pct']:
        years = pct_trends.index.values
        values = pct_trends[var].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(years, values)

        sig_level = '***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'NS'

        pct_significance[var] = {
            'slope': slope,
            'r_squared': r_value**2,
            'p_value': p_value,
            'significance': sig_level
        }

        print(f"  {var:20s}: slope={slope:8.6f}, R2={r_value**2:.3f}, p={p_value:.4f} {sig_level}")

    results['pct_trends'] = pct_trends
    results['pct_significance'] = pct_significance

    # ========================================================================
    # 5.2 Real Per-FTE Spending Trends
    # ========================================================================
    print("\n[B. Real Per-FTE Spending Trends (2018 dollars)]")

    real_per_fte_trends = df.groupby('year').agg({
        'admin_per_fte_real': 'median',
        'instruction_per_fte_real': 'median',
        'total_per_fte_real': 'median'
    }).round(2)

    print("\nAnnual medians:")
    print(real_per_fte_trends)

    # 2018 -> 2023 real change
    if 2018 in real_per_fte_trends.index and 2023 in real_per_fte_trends.index:
        real_change = (
            (real_per_fte_trends.loc[2023] - real_per_fte_trends.loc[2018]) /
            real_per_fte_trends.loc[2018] * 100
        ).round(1)
        print("\n2018 -> 2023 real change (%):")
        print(real_change)

    # Trend significance
    print("\nTrend Significance Tests:")
    real_significance = {}
    for var in real_per_fte_trends.columns:
        years = real_per_fte_trends.index.values
        values = real_per_fte_trends[var].values
        slope, intercept, r_value, p_value, std_err = stats.linregress(years, values)

        sig_level = '***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else 'NS'

        real_significance[var] = {
            'slope': slope,
            'r_squared': r_value**2,
            'p_value': p_value,
            'significance': sig_level
        }

        print(f"  {var:25s}: slope={slope:8.2f}, R2={r_value**2:.3f}, p={p_value:.4f} {sig_level}")

    results['real_per_fte_trends'] = real_per_fte_trends
    results['real_significance'] = real_significance

    # ========================================================================
    # 5.3 Public vs. Private Comparison
    # ========================================================================
    print("\n[C. Public vs. Private Comparison]")

    type_results = {}
    for inst_type in ['Public', 'Private']:
        print(f"\n--- {inst_type} Institutions ---")

        type_data = df[df['type'] == inst_type]

        # Real per-FTE spending
        type_real = type_data.groupby('year').agg({
            'admin_per_fte_real': 'median',
            'instruction_per_fte_real': 'median',
            'total_per_fte_real': 'median'
        }).round(0)

        print("\nReal per-FTE spending (2018$):")
        print(type_real)

        # Change rate
        type_change = None
        if 2018 in type_real.index and 2023 in type_real.index:
            type_change = (
                (type_real.loc[2023] - type_real.loc[2018]) /
                type_real.loc[2018] * 100
            ).round(1)
            print("\n2018 -> 2023 change (%):")
            print(type_change)

        type_results[inst_type] = {
            'real_trends': type_real,
            'change': type_change
        }

    results['by_type'] = type_results

    return results


# ============================================================================
# Part 5: Visualization
# ============================================================================

def create_comprehensive_visualization(df, output_path=OUTPUT_VISUALIZATION):
    """
    Create a comprehensive trend visualization with 12 subplots (4 rows x 3 columns).

    Layout:
    - Row 1: Spending share trends
    - Row 2: Nominal per-FTE spending
    - Row 3: Real per-FTE spending
    - Row 4: Real absolute spending + summary of changes

    Parameters
    ----------
    df : pandas.DataFrame
        Fully processed data.
    output_path : str
        Output file path.
    """
    print("\n" + "=" * 80)
    print("STEP 6: Creating Visualizations")
    print("=" * 80)

    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")

    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)

    years = sorted(df['year'].unique())

    # ========================================================================
    # Row 1: Spending Shares
    # ========================================================================

    # 1.1 Overall composition
    ax1 = fig.add_subplot(gs[0, 0])
    overall_pct = df.groupby('year')[['admin_pct', 'instruction_pct', 'research_pct']].mean() * 100
    ax1.plot(years, overall_pct['admin_pct'], 'o-', linewidth=2.5, markersize=8, label='Administrative')
    ax1.plot(years, overall_pct['instruction_pct'], 's-', linewidth=2.5, markersize=8, label='Instructional')
    ax1.plot(years, overall_pct['research_pct'], '^-', linewidth=2.5, markersize=8, label='Research')
    ax1.set_title('Overall Spending Composition', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Year')
    ax1.set_ylabel('% of Total Budget')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 1.2 Admin %: Public vs Private
    ax2 = fig.add_subplot(gs[0, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_pct'].mean() * 100
        ax2.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax2.set_title('Admin %: Public vs Private', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Admin %')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 1.3 Instruction %: Public vs Private
    ax3 = fig.add_subplot(gs[0, 2])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['instruction_pct'].mean() * 100
        ax3.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax3.set_title('Instruction %: Public vs Private', fontsize=13, fontweight='bold')
    ax3.set_xlabel('Year')
    ax3.set_ylabel('Instruction %')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # ========================================================================
    # Row 2: Nominal Per-FTE Spending
    # ========================================================================

    # 2.1 Nominal admin per FTE
    ax4 = fig.add_subplot(gs[1, 0])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_per_fte'].median()
        ax4.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax4.set_title('Nominal Admin per FTE', fontsize=13, fontweight='bold')
    ax4.set_xlabel('Year')
    ax4.set_ylabel('$ per FTE')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 2.2 Nominal instruction per FTE
    ax5 = fig.add_subplot(gs[1, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['instruction_per_fte'].median()
        ax5.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax5.set_title('Nominal Instruction per FTE', fontsize=13, fontweight='bold')
    ax5.set_xlabel('Year')
    ax5.set_ylabel('$ per FTE')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 2.3 Nominal total per FTE
    ax6 = fig.add_subplot(gs[1, 2])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['total_per_fte'].median()
        ax6.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax6.set_title('Nominal Total per FTE', fontsize=13, fontweight='bold')
    ax6.set_xlabel('Year')
    ax6.set_ylabel('$ per FTE')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # ========================================================================
    # Row 3: Real Per-FTE Spending
    # ========================================================================

    # 3.1 Real admin per FTE
    ax7 = fig.add_subplot(gs[2, 0])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_per_fte_real'].median()
        ax7.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax7.set_title('Real Admin per FTE (2018$)', fontsize=13, fontweight='bold')
    ax7.set_xlabel('Year')
    ax7.set_ylabel('$ per FTE (2018 dollars)')
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # 3.2 Real instruction per FTE
    ax8 = fig.add_subplot(gs[2, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['instruction_per_fte_real'].median()
        ax8.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax8.set_title('Real Instruction per FTE (2018$)', fontsize=13, fontweight='bold')
    ax8.set_xlabel('Year')
    ax8.set_ylabel('$ per FTE (2018 dollars)')
    ax8.legend()
    ax8.grid(True, alpha=0.3)

    # 3.3 Real total per FTE
    ax9 = fig.add_subplot(gs[2, 2])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['total_per_fte_real'].median()
        ax9.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax9.set_title('Real Total per FTE (2018$)', fontsize=13, fontweight='bold')
    ax9.set_xlabel('Year')
    ax9.set_ylabel('$ per FTE (2018 dollars)')
    ax9.legend()
    ax9.grid(True, alpha=0.3)

    # ========================================================================
    # Row 4: Real Absolute Spending + Change Summary
    # ========================================================================

    # 4.1 Real admin spending (absolute)
    ax10 = fig.add_subplot(gs[3, 0])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_real'].median() / 1e6
        ax10.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax10.set_title('Real Admin Spending (2018$)', fontsize=13, fontweight='bold')
    ax10.set_xlabel('Year')
    ax10.set_ylabel('Median ($ millions)')
    ax10.legend()
    ax10.grid(True, alpha=0.3)

    # 4.2 Real instruction spending (absolute)
    ax11 = fig.add_subplot(gs[3, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['instruction_real'].median() / 1e6
        ax11.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax11.set_title('Real Instruction Spending (2018$)', fontsize=13, fontweight='bold')
    ax11.set_xlabel('Year')
    ax11.set_ylabel('Median ($ millions)')
    ax11.legend()
    ax11.grid(True, alpha=0.3)

    # 4.3 2018 -> 2023 change summary (bar chart)
    ax12 = fig.add_subplot(gs[3, 2])
    categories = ['Admin\n%', 'Instruction\n%', 'Admin\nper FTE\n(Real)', 'Instruction\nper FTE\n(Real)']

    public_2018 = df[(df['type'] == 'Public') & (df['year'] == 2018)]
    public_2023 = df[(df['type'] == 'Public') & (df['year'] == 2023)]
    private_2018 = df[(df['type'] == 'Private') & (df['year'] == 2018)]
    private_2023 = df[(df['type'] == 'Private') & (df['year'] == 2023)]

    public_changes = [
        (public_2023['admin_pct'].mean() - public_2018['admin_pct'].mean()) / public_2018['admin_pct'].mean() * 100,
        (public_2023['instruction_pct'].mean() - public_2018['instruction_pct'].mean()) / public_2018['instruction_pct'].mean() * 100,
        (public_2023['admin_per_fte_real'].median() - public_2018['admin_per_fte_real'].median()) / public_2018['admin_per_fte_real'].median() * 100,
        (public_2023['instruction_per_fte_real'].median() - public_2018['instruction_per_fte_real'].median()) / public_2018['instruction_per_fte_real'].median() * 100
    ]

    private_changes = [
        (private_2023['admin_pct'].mean() - private_2018['admin_pct'].mean()) / private_2018['admin_pct'].mean() * 100,
        (private_2023['instruction_pct'].mean() - private_2018['instruction_pct'].mean()) / private_2018['instruction_pct'].mean() * 100,
        (private_2023['admin_per_fte_real'].median() - private_2018['admin_per_fte_real'].median()) / private_2018['admin_per_fte_real'].median() * 100,
        (private_2023['instruction_per_fte_real'].median() - private_2018['instruction_per_fte_real'].median()) / private_2018['instruction_per_fte_real'].median() * 100
    ]

    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax12.bar(x - width/2, public_changes, width, label='Public', color='#2E86AB')
    bars2 = ax12.bar(x + width/2, private_changes, width, label='Private', color='#A23B72')

    ax12.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    ax12.set_title('2018 -> 2023 Changes', fontsize=13, fontweight='bold')
    ax12.set_ylabel('% Change')
    ax12.set_xticks(x)
    ax12.set_xticklabels(categories, fontsize=9)
    ax12.legend()
    ax12.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax12.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:+.1f}%', ha='center',
                     va='bottom' if height > 0 else 'top', fontsize=8)

    # Overall title
    fig.suptitle('U.S. Higher Education Spending Trends (2018-2023)',
                 fontsize=16, fontweight='bold', y=0.995)

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nVisualization saved: {output_path}")

    plt.close()


# ============================================================================
# Part 6: Exporting Results
# ============================================================================

def export_results(df_corrected, trends, output_data=OUTPUT_CORRECTED_DATA,
                   output_summary=OUTPUT_SUMMARY_STATS):
    """
    Export corrected data and statistical summary.

    Parameters
    ----------
    df_corrected : pandas.DataFrame
        Fully processed and corrected data.
    trends : dict
        Trend analysis results.
    output_data : str
        Output path for corrected data CSV.
    output_summary : str
        Output path for statistical summary CSV.
    """
    print("\n" + "=" * 80)
    print("STEP 7: Exporting Results")
    print("=" * 80)

    # Save corrected data
    df_corrected.to_csv(output_data, index=False)
    print(f"\nCorrected data saved: {output_data}")
    print(f"  {len(df_corrected)} rows, {len(df_corrected.columns)} columns")

    # Build statistical summary
    summary_rows = []
    for year in trends['pct_trends'].index:
        row = {
            'year': year,
            'admin_pct': trends['pct_trends'].loc[year, 'admin_pct'],
            'instruction_pct': trends['pct_trends'].loc[year, 'instruction_pct'],
            'admin_per_fte_real': trends['real_per_fte_trends'].loc[year, 'admin_per_fte_real'],
            'instruction_per_fte_real': trends['real_per_fte_trends'].loc[year, 'instruction_per_fte_real']
        }
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_summary, index=False)
    print(f"Statistical summary saved: {output_summary}")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run the complete analysis pipeline."""
    print("\n" + "=" * 80)
    print("U.S. Higher Education Spending Trends Analysis (2018-2023)")
    print("=" * 80)
    print("\nStarting analysis...\n")

    # Step 1: Load data
    df = load_and_inspect_data(INPUT_FILE)

    # Step 2: Diagnose FTE anomaly
    diagnosis = diagnose_fte_anomaly(df)

    # Step 3: Correct FTE data
    df_corrected = correct_fte_data(df)
    df_corrected = recalculate_per_fte_metrics(df_corrected)

    # Step 4: Inflation adjustment
    df_corrected = add_inflation_adjusted_metrics(df_corrected)

    # Step 5: Trend analysis
    trends = calculate_trends(df_corrected)

    # Step 6: Visualization
    create_comprehensive_visualization(df_corrected)

    # Step 7: Export results
    export_results(df_corrected, trends)

    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)
    print("\nOutput files:")
    print(f"  1. Corrected data:       {OUTPUT_CORRECTED_DATA}")
    print(f"  2. Statistical summary:  {OUTPUT_SUMMARY_STATS}")
    print(f"  3. Visualization:        {OUTPUT_VISUALIZATION}")
    print()


if __name__ == "__main__":
    main()
