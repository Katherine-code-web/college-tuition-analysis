"""
U.S. Higher Education Spending Trends Analysis (2018-2023)
===========================================================

This script performs comprehensive time-series analysis of higher education spending，包括：
1. FTE Data Correction（2020-2023年異常值處理）
2. Inflation Adjustment（CPI deflator）
3. 支出佔比Trend Analysis
4. 名目vs實質支出對比
5. Public vs Private比較分析
6. 統計顯著性檢驗

Author: Bo-Ru
Date: 2026-02-04
Data Source: IPEDS (Integrated Postsecondary Education Data System)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 配置參數
# ============================================================================

# Input file path
INPUT_FILE = 'panel_2018_2023.csv'

# Output file paths
OUTPUT_CORRECTED_DATA = 'panel_2018_2023_corrected.csv'
OUTPUT_SUMMARY_STATS = 'trend_analysis_summary.csv'
OUTPUT_VISUALIZATION = 'trend_analysis_comprehensive.png'

# CPI調整因子（2018年為基準=1.00）
# Data source: U.S. Bureau of Labor Statistics
CPI_DEFLATOR = {
    2018: 1.00,  # Base year
    2019: 1.02,  # +2%
    2020: 1.03,  # +1%
    2021: 1.08,  # +5%
    2022: 1.16,  # +8%
    2023: 1.20   # +4%
}

# FTE異常閾值（2020/2019比值超過此值視為異常）
FTE_ANOMALY_THRESHOLD = 2.0

# 統計顯著性水平
ALPHA_LEVEL = 0.05

# ============================================================================
# 第一部分：數據載入與初步檢查
# ============================================================================

def load_and_inspect_data(filepath):
    """
    載入原始數據並進rows初步檢查
    
    Parameters:
    -----------
    filepath : str
        數據文件路徑
        
    Returns:
    --------
    df : pandas.DataFrame
        載入的數據框
    """
    print("=" * 80)
    print("STEP 1: Loading Data")
    print("=" * 80)
    
    # 讀取CSV
    df = pd.read_csv(filepath)
    
    # 基本資訊
    print(f"\nData dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Time range: {df['year'].min()} - {df['year'].max()}")
    print(f"Number of schools: {df['UNITID'].nunique()}")
    
    # 年度分布
    print("\nObservations by year:")
    print(df['year'].value_counts().sort_index())
    
    # Distribution by institution type
    print("\nDistribution by institution type:")
    print(df['type'].value_counts())
    
    # 缺失值檢查
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print("\nMissing values statistics (showing only columns with missing values):")
        print(missing[missing > 0])
    
    return df

# ============================================================================
# 第二部分：FTE Data Correction
# ============================================================================

def diagnose_fte_anomaly(df):
    """
    診斷FTE數據異常問題
    
    背景: 2020年FTE數據出現系統性飆升（+258%），可能因COVID-19
    期間統計方法變更或遠程學習學生計算方式改變。
    
    Parameters:
    -----------
    df : pandas.DataFrame
        原始數據
        
    Returns:
    --------
    diagnosis : dict
        診斷結果統計
    """
    print("\n" + "=" * 80)
    print("STEP 2: FTE Data Anomaly Diagnosis")
    print("=" * 80)
    
    # 計算年度Change率
    df_sorted = df.sort_values(['UNITID', 'year']).copy()
    df_sorted['fte_change'] = df_sorted.groupby('UNITID')['fte'].pct_change(fill_method=None)
    
    diagnosis = {}
    
    # 檢查各年度異常比例
    for year in range(2019, 2024):
        if year in df['year'].values:
            changes = df_sorted[df_sorted['year'] == year]['fte_change']
            n_anomaly = (changes.abs() > 1.0).sum()  # >100%Change視為異常
            n_total = changes.notna().sum()
            
            diagnosis[year] = {
                'anomaly_count': n_anomaly,
                'total_count': n_total,
                'anomaly_pct': n_anomaly / n_total * 100 if n_total > 0 else 0,
                'mean_change': changes.mean() * 100,
                'median_change': changes.median() * 100
            }
            
            print(f"\n{year-1}→{year}:")
            print(f"  異常Number of schools: {n_anomaly} / {n_total} ({diagnosis[year]['anomaly_pct']:.1f}%)")
            print(f"  Mean change rate: {diagnosis[year]['mean_change']:.1f}%")
            print(f"  Median change rate: {diagnosis[year]['median_change']:.1f}%")
    
    # 重點標記2020年問題
    if 2020 in diagnosis:
        print("\n" + "!" * 80)
        print(f"⚠️  Severe anomaly detected in 2020：{diagnosis[2020]['anomaly_pct']:.1f}%schoolsFTE異常增長")
        print(f"   Mean growth rate: {diagnosis[2020]['mean_change']:.1f}%")
        print("!" * 80)
    
    return diagnosis

def correct_fte_data(df, threshold=FTE_ANOMALY_THRESHOLD):
    """
    修正FTE數據異常
    
    策略: 對於2020年FTE異常飆升schools（2020/2019 > threshold），
    使用2018-2019的正常增長率外推2020-2023年的FTE值。
    
    Parameters:
    -----------
    df : pandas.DataFrame
        原始數據
    threshold : float
        異常判定閾值（默認2.0，即增長>100%）
        
    Returns:
    --------
    df_corrected : pandas.DataFrame
        修正後的數據
    """
    print("\n" + "=" * 80)
    print("STEP 3: FTE Data Correction")
    print("=" * 80)
    
    df_corrected = df.copy()
    
    # 創建透視表以便操作
    fte_pivot = df.pivot(index='UNITID', columns='year', values='fte')
    
    # 識別需要修正schools
    if 2019 in fte_pivot.columns and 2020 in fte_pivot.columns:
        needs_correction = (
            (fte_pivot[2020] / fte_pivot[2019] > threshold) & 
            fte_pivot[2020].notna() & 
            fte_pivot[2019].notna()
        )
        n_corrected = needs_correction.sum()
        print(f"\n需要修正的Number of schools: {n_corrected}")
        
        # 對每所需要修正schools
        for unitid in fte_pivot[needs_correction].index:
            # 計算2018-2019的正常增長率
            fte_2018 = fte_pivot.loc[unitid, 2018] if 2018 in fte_pivot.columns else np.nan
            fte_2019 = fte_pivot.loc[unitid, 2019]
            
            if pd.notna(fte_2018) and pd.notna(fte_2019):
                # 計算增長率
                growth_rate = (fte_2019 - fte_2018) / fte_2018
            else:
                # 如果沒有2018數據，假設零增長
                growth_rate = 0.0
            
            # 外推2020-2023
            fte_2019_value = fte_2019
            for year in [2020, 2021, 2022, 2023]:
                if year in df['year'].values:
                    fte_corrected = fte_2019_value * ((1 + growth_rate) ** (year - 2019))
                    df_corrected.loc[
                        (df_corrected['UNITID'] == unitid) & 
                        (df_corrected['year'] == year), 
                        'fte'
                    ] = fte_corrected
        
        print(f"Correction complete! Processed {n_corrected} schools for 2020-2023 FTE data")
    
    return df_corrected

def recalculate_per_fte_metrics(df):
    """
    Recalculating per_fte metrics
    
    在FTE修正後，需要重新計算所有Per-FTE spending指標。
    
    Parameters:
    -----------
    df : pandas.DataFrame
        修正FTE後的數據
        
    Returns:
    --------
    df : pandas.DataFrame
        更新per_fte指標後的數據
    """
    print("\nRecalculating per_fte metrics...")
    
    # 重新計算
    df['admin_per_fte'] = df['admin'] / df['fte']
    df['instruction_per_fte'] = df['instruction'] / df['fte']
    df['state_per_fte'] = df['state'] / df['fte']
    df['total_per_fte'] = df['total'] / df['fte']
    
    # 處理無限值和NaN
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    print("✓ per_fte metrics updated")
    
    return df

# ============================================================================
# 第三部分：Inflation Adjustment
# ============================================================================

def add_inflation_adjusted_metrics(df, cpi_deflator=CPI_DEFLATOR):
    """
    添加Inflation Adjustment後的實質指標
    
    將所有名目金額調整至2018年美元（constant dollars）。
    這讓我們能看到"實際購買力"的Change。
    
    Parameters:
    -----------
    df : pandas.DataFrame
        數據
    cpi_deflator : dict
        各年度CPI調整因子
        
    Returns:
    --------
    df : pandas.DataFrame
        添加實質指標後的數據
    """
    print("\n" + "=" * 80)
    print("STEP 4: Inflation Adjustment")
    print("=" * 80)
    
    print("\nCPI Deflator (2018=1.00):")
    for year, deflator in sorted(cpi_deflator.items()):
        cumulative_inflation = (deflator - 1.0) * 100
        print(f"  {year}: {deflator:.2f} (Cumulative inflation: {cumulative_inflation:+.1f}%)")
    
    # 計算實質值（絕對金額）
    df['admin_real'] = df.apply(
        lambda x: x['admin'] / cpi_deflator[x['year']], axis=1
    )
    df['instruction_real'] = df.apply(
        lambda x: x['instruction'] / cpi_deflator[x['year']], axis=1
    )
    df['total_real'] = df.apply(
        lambda x: x['total'] / cpi_deflator[x['year']], axis=1
    )
    
    # 計算實質值（人均）
    df['admin_per_fte_real'] = df.apply(
        lambda x: x['admin_per_fte'] / cpi_deflator[x['year']], axis=1
    )
    df['instruction_per_fte_real'] = df.apply(
        lambda x: x['instruction_per_fte'] / cpi_deflator[x['year']], axis=1
    )
    df['total_per_fte_real'] = df.apply(
        lambda x: x['total_per_fte'] / cpi_deflator[x['year']], axis=1
    )
    
    print("\n✓ Real metrics added")
    print("  - *_real: Institutional-level real spending（2018年美元）")
    print("  - *_per_fte_real: Per-FTE real spending（2018年美元）")
    
    return df

# ============================================================================
# 第四部分：Trend Analysis
# ============================================================================

def calculate_trends(df):
    """
    計算完整的趨勢統計
    
    包括：
    1. Spending Share Trends
    2. Nominal Per-FTE Spending Trends
    3. 實質Per-FTE spending趨勢
    4. Public vs Private分組趨勢
    
    Parameters:
    -----------
    df : pandas.DataFrame
        完整處理後的數據
        
    Returns:
    --------
    results : dict
        Contains所有Trend Analysis結果的字典
    """
    print("\n" + "=" * 80)
    print("STEP 5: Trend Analysis")
    print("=" * 80)
    
    results = {}
    
    # ========================================================================
    # 5.1 整體Spending Share Trends
    # ========================================================================
    print("\n【A. Spending Share Trends】")
    
    pct_trends = df.groupby('year').agg({
        'admin_pct': 'mean',
        'instruction_pct': 'mean',
        'research_pct': 'mean'
    }).round(4)
    
    print("\nAnnual average shares:")
    print(pct_trends)
    
    # 計算2018→2023Change
    if 2018 in pct_trends.index and 2023 in pct_trends.index:
        pct_change = (
            (pct_trends.loc[2023] - pct_trends.loc[2018]) / 
            pct_trends.loc[2018] * 100
        ).round(1)
        print("\n2018→2023Change:")
        print(pct_change)
    
    # Trend Significance Tests
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
        
        print(f"  {var:20s}: slope={slope:8.6f}, R²={r_value**2:.3f}, p={p_value:.4f} {sig_level}")
    
    results['pct_trends'] = pct_trends
    results['pct_significance'] = pct_significance
    
    # ========================================================================
    # 5.2 實質Per-FTE spending趨勢
    # ========================================================================
    print("\n【B. 實質Per-FTE spending趨勢】(2018年美元)")
    
    real_per_fte_trends = df.groupby('year').agg({
        'admin_per_fte_real': 'median',
        'instruction_per_fte_real': 'median',
        'total_per_fte_real': 'median'
    }).round(2)
    
    print("\n年度median:")
    print(real_per_fte_trends)
    
    # 計算Change
    if 2018 in real_per_fte_trends.index and 2023 in real_per_fte_trends.index:
        real_change = (
            (real_per_fte_trends.loc[2023] - real_per_fte_trends.loc[2018]) / 
            real_per_fte_trends.loc[2018] * 100
        ).round(1)
        print("\n2018→2023實質Change:")
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
        
        print(f"  {var:25s}: slope={slope:8.2f}, R²={r_value**2:.3f}, p={p_value:.4f} {sig_level}")
    
    results['real_per_fte_trends'] = real_per_fte_trends
    results['real_significance'] = real_significance
    
    # ========================================================================
    # 5.3 Public vs Private 對比
    # ========================================================================
    print("\n【C. Public vs Private 對比】")
    
    type_results = {}
    for inst_type in ['Public', 'Private']:
        print(f"\n--- {inst_type} Universities ---")
        
        type_data = df[df['type'] == inst_type]
        
        # 實質Per-FTE spending
        type_real = type_data.groupby('year').agg({
            'admin_per_fte_real': 'median',
            'instruction_per_fte_real': 'median',
            'total_per_fte_real': 'median'
        }).round(0)
        
        print("\n實質Per-FTE spending (2018$):")
        print(type_real)
        
        # Change率
        if 2018 in type_real.index and 2023 in type_real.index:
            type_change = (
                (type_real.loc[2023] - type_real.loc[2018]) / 
                type_real.loc[2018] * 100
            ).round(1)
            print("\n2018→2023Change:")
            print(type_change)
        
        type_results[inst_type] = {
            'real_trends': type_real,
            'change': type_change if 2018 in type_real.index and 2023 in type_real.index else None
        }
    
    results['by_type'] = type_results
    
    return results

# ============================================================================
# 第五部分：視覺化
# ============================================================================

def create_comprehensive_visualization(df, output_path=OUTPUT_VISUALIZATION):
    """
    創建完整的趨勢視覺化
    
    Contains4rows3columns共12個子圖，展示：
    - Spending Share Trends
    - 名目Per-FTE spending
    - 實質Per-FTE spending
    - 實質絕對支出
    - Public vs Private對比
    
    Parameters:
    -----------
    df : pandas.DataFrame
        完整處理後的數據
    output_path : str
        Output file paths
    """
    print("\n" + "=" * 80)
    print("STEP 6: Creating Visualizations")
    print("=" * 80)
    
    # 設定風格
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")
    
    fig = plt.figure(figsize=(20, 14))
    gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
    
    years = sorted(df['year'].unique())
    
    # ========================================================================
    # 第一rows：支出佔比
    # ========================================================================
    
    # 1.1 整體佔比
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
    
    # 1.2 Admin佔比: Public vs Private
    ax2 = fig.add_subplot(gs[0, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_pct'].mean() * 100
        ax2.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax2.set_title('Admin %: Public vs Private', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Year')
    ax2.set_ylabel('Admin %')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 1.3 Instruction佔比: Public vs Private
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
    # 第二rows：名目Per-FTE spending
    # ========================================================================
    
    # 2.1 Admin per FTE (名目)
    ax4 = fig.add_subplot(gs[1, 0])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_per_fte'].median()
        ax4.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax4.set_title('Nominal Admin per FTE', fontsize=13, fontweight='bold')
    ax4.set_xlabel('Year')
    ax4.set_ylabel('$ per FTE')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 2.2 Instruction per FTE (名目)
    ax5 = fig.add_subplot(gs[1, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['instruction_per_fte'].median()
        ax5.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax5.set_title('Nominal Instruction per FTE', fontsize=13, fontweight='bold')
    ax5.set_xlabel('Year')
    ax5.set_ylabel('$ per FTE')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    
    # 2.3 Total per FTE (名目)
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
    # 第三rows：實質Per-FTE spending
    # ========================================================================
    
    # 3.1 Admin per FTE (實質)
    ax7 = fig.add_subplot(gs[2, 0])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_per_fte_real'].median()
        ax7.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax7.set_title('Real Admin per FTE (2018$)', fontsize=13, fontweight='bold')
    ax7.set_xlabel('Year')
    ax7.set_ylabel('$ per FTE (2018 dollars)')
    ax7.legend()
    ax7.grid(True, alpha=0.3)
    
    # 3.2 Instruction per FTE (實質)
    ax8 = fig.add_subplot(gs[2, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['instruction_per_fte_real'].median()
        ax8.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax8.set_title('Real Instruction per FTE (2018$)', fontsize=13, fontweight='bold')
    ax8.set_xlabel('Year')
    ax8.set_ylabel('$ per FTE (2018 dollars)')
    ax8.legend()
    ax8.grid(True, alpha=0.3)
    
    # 3.3 Total per FTE (實質)
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
    # 第四rows：實質絕對支出 + 總結
    # ========================================================================
    
    # 4.1 Admin支出 (實質絕對)
    ax10 = fig.add_subplot(gs[3, 0])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['admin_real'].median() / 1e6
        ax10.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax10.set_title('Real Admin Spending (2018$)', fontsize=13, fontweight='bold')
    ax10.set_xlabel('Year')
    ax10.set_ylabel('Median ($ millions)')
    ax10.legend()
    ax10.grid(True, alpha=0.3)
    
    # 4.2 Instruction支出 (實質絕對)
    ax11 = fig.add_subplot(gs[3, 1])
    for inst_type, marker, color in [('Public', 'o', '#2E86AB'), ('Private', 's', '#A23B72')]:
        data = df[df['type'] == inst_type].groupby('year')['instruction_real'].median() / 1e6
        ax11.plot(years, data, marker=marker, linewidth=2.5, markersize=8, label=inst_type, color=color)
    ax11.set_title('Real Instruction Spending (2018$)', fontsize=13, fontweight='bold')
    ax11.set_xlabel('Year')
    ax11.set_ylabel('Median ($ millions)')
    ax11.legend()
    ax11.grid(True, alpha=0.3)
    
    # 4.3 Change率對比圖
    ax12 = fig.add_subplot(gs[3, 2])
    categories = ['Admin\n%', 'Instruction\n%', 'Admin\nper FTE\n(Real)', 'Instruction\nper FTE\n(Real)']
    
    # 計算Change率
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
    ax12.set_title('2018→2023 Changes', fontsize=13, fontweight='bold')
    ax12.set_ylabel('% Change')
    ax12.set_xticks(x)
    ax12.set_xticklabels(categories, fontsize=9)
    ax12.legend()
    ax12.grid(True, alpha=0.3, axis='y')
    
    # 添加數值標籤
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax12.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:+.1f}%', ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
    
    # 總標題
    fig.suptitle('U.S. Higher Education Spending Trends (2018-2023)', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 保存
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Visualization saved: {output_path}")
    
    plt.close()

# ============================================================================
# 第六部分：Exporting Results
# ============================================================================

def export_results(df_corrected, trends, output_data=OUTPUT_CORRECTED_DATA, 
                   output_summary=OUTPUT_SUMMARY_STATS):
    """
    導出修正後的數據和Statistical summary
    
    Parameters:
    -----------
    df_corrected : pandas.DataFrame
        修正並處理完成的數據
    trends : dict
        Trend Analysis結果
    output_data : str
        修正數據輸出路徑
    output_summary : str
        Statistical summary輸出路徑
    """
    print("\n" + "=" * 80)
    print("STEP 7: Exporting Results")
    print("=" * 80)
    
    # 保存修正後的完整數據
    df_corrected.to_csv(output_data, index=False)
    print(f"\n✓ Corrected data saved: {output_data}")
    print(f"  Contains {len(df_corrected)} rows, {len(df_corrected.columns)} columns")
    
    # 創建Statistical summary
    summary_rows = []
    
    # 整體趨勢
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
    print(f"✓ Statistical summary saved: {output_summary}")

# ============================================================================
# 主程式
# ============================================================================

def main():
    """
    主函數：執rows完整的分析流程
    """
    print("\n" + "=" * 80)
    print("U.S. Higher Education Spending Trends Analysis (2018-2023)")
    print("=" * 80)
    print("\nStarting analysis...\n")
    
    # Step 1: Loading Data
    df = load_and_inspect_data(INPUT_FILE)
    
    # Step 2: 診斷FTE問題
    diagnosis = diagnose_fte_anomaly(df)
    
    # Step 3: 修正FTE
    df_corrected = correct_fte_data(df)
    df_corrected = recalculate_per_fte_metrics(df_corrected)
    
    # Step 4: Inflation Adjustment
    df_corrected = add_inflation_adjusted_metrics(df_corrected)
    
    # Step 5: Trend Analysis
    trends = calculate_trends(df_corrected)
    
    # Step 6: 視覺化
    create_comprehensive_visualization(df_corrected)
    
    # Step 7: Exporting Results
    export_results(df_corrected, trends)
    
    print("\n" + "=" * 80)
    print("✓ Analysis complete!")
    print("=" * 80)
    print("\nOutput files:")
    print(f"  1. Corrected data: {OUTPUT_CORRECTED_DATA}")
    print(f"  2. Statistical summary: {OUTPUT_SUMMARY_STATS}")
    print(f"  3. Visualization: {OUTPUT_VISUALIZATION}")
    print("\nThank you for using! Please contact the author with any questions。\n")

if __name__ == "__main__":
    main()
