# Google Colab Usage Guide

## 🚀 Quick Start

### Step 1: Open Notebook

1. Visit [Google Colab](https://colab.research.google.com/)
2. Click `File` → `Upload notebook`
3. Upload `Higher_Education_Spending_Analysis_Colab.ipynb`

**Or visit directly (if uploaded to GitHub):**
```
https://colab.research.google.com/github/your-username/your-repo/blob/main/Higher_Education_Spending_Analysis_Colab.ipynb
```

### Step 2: Prepare Data

Ensure you have the `panel_2018_2023.csv` file.

### Step 3: Run in Order

Click `Runtime` → `Run all` or execute each cell sequentially.

---

## 📝 Notebook Structure

### Part 0: Environment Setup
- Install packages
- Upload data file
- Configure parameters

### Part 1: Load Data
- Read CSV
- Check data integrity
- Basic statistics

### Part 2: FTE Anomaly Diagnosis
- Identify 2020 data issues
- Visualize anomaly distribution
- Quantify affected scope

### Part 3: FTE Data Correction
- Correct anomalous values
- Recalculate per_fte metrics
- Validate correction effects

### Part 4: Inflation Adjustment
- Add CPI deflator
- Calculate real metrics
- Create *_real variables

### Part 5: Trend Analysis
- Spending share trends
- Real per-FTE spending trends
- Public vs Private comparison
- Statistical significance tests

### Part 6: Visualization
- Create 12 subplots
- Comprehensive display

### Part 7: Download Results
- Save corrected data
- Create statistical summary
- Auto-download

---

## 💡 Usage Tips

### Modify CPI Data

In **Configure Parameters** cell:
```python
CPI_DEFLATOR = {
    2018: 1.00,
    2019: 1.02,  # Modify here
    2020: 1.03,
    # ...
}
```

### Analyze Specific Institution Types Only

Add filter before analysis:
```python
# Analyze Public only
df_corrected = df_corrected[df_corrected['type'] == 'Public']

# Analyze specific state only
df_corrected = df_corrected[df_corrected['STABBR'] == 'CA']
```

### Adjust Anomaly Threshold

```python
FTE_ANOMALY_THRESHOLD = 1.5  # Stricter
# or
FTE_ANOMALY_THRESHOLD = 3.0  # More lenient
```

### Save Charts

Add after visualization cell:
```python
plt.savefig('my_chart.png', dpi=300, bbox_inches='tight')
files.download('my_chart.png')
```

---

## 🔧 Common Issues

### Q1: File Upload Failed?

**Solution:**
1. Confirm correct filename: `panel_2018_2023.csv`
2. Check file size (Colab limit 100MB)
3. Try re-uploading

### Q2: Runtime Too Long?

**Optimization:**
```python
# Use sample data for testing
df_sample = df.sample(n=1000, random_state=42)
```

### Q3: Out of Memory?

**Solution:**
```python
# Load only necessary columns
columns_to_load = ['UNITID', 'year', 'type', 'fte', 'admin', 'instruction']
df = pd.read_csv(filename, usecols=columns_to_load)
```

### Q4: How to Restart?

1. Click `Runtime` → `Restart runtime`
2. Re-run all cells

### Q5: Charts Display Incomplete?

```python
# Add before visualization
%matplotlib inline
plt.rcParams['figure.max_open_warning'] = 50
```

---

## 📊 Output Files

After completion, generates:

1. **panel_2018_2023_corrected.csv**
   - Corrected complete data
   - Includes all real metrics
   - Ready for further analysis

2. **trend_analysis_summary.csv**
   - Annual statistical summary
   - Key metric changes

3. **Visualization Charts**
   - Displayed directly in notebook
   - Can screenshot to save

---

## 🎯 Advanced Usage

### Create Interactive Visualizations

```python
import plotly.express as px

fig = px.line(
    df_corrected.groupby(['year', 'type'])['instruction_per_fte_real'].median().reset_index(),
    x='year', 
    y='instruction_per_fte_real', 
    color='type',
    title='Interactive: Real Instruction per FTE'
)
fig.show()
```

### Export to Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')

# Save to Drive
df_corrected.to_csv('/content/drive/MyDrive/corrected_data.csv', index=False)
```

### Connect to GitHub

```python
# Clone your repo
!git clone https://github.com/your-username/your-repo.git

# Change directory
%cd your-repo

# Run analysis
!python analyze_spending_trends.py
```

---

## 🆘 Get Help

### Method 1: Check Error Messages
Most error messages clearly indicate the problem.

### Method 2: Use Built-in Help
```python
?pd.read_csv  # View function documentation
help(stats.linregress)  # Detailed docs
```

### Method 3: Print Intermediate Results
```python
print(df.shape)  # Check data dimensions
print(df.columns)  # View column names
print(df.head())  # Preview data
```

### Method 4: Step-by-Step Debugging
Don't run all cells at once; execute one by one to easily spot issues.

---

## 📚 Further Learning

### Data Analysis
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [NumPy Tutorial](https://numpy.org/doc/stable/user/quickstart.html)

### Visualization
- [Matplotlib Gallery](https://matplotlib.org/stable/gallery/index.html)
- [Seaborn Tutorial](https://seaborn.pydata.org/tutorial.html)

### Statistical Testing
- [SciPy Stats](https://docs.scipy.org/doc/scipy/reference/stats.html)
- [Linear Regression](https://en.wikipedia.org/wiki/Linear_regression)

### Google Colab
- [Official Guide](https://colab.research.google.com/notebooks/intro.ipynb)
- [Tips & Tricks](https://colab.research.google.com/notebooks/snippets/advanced_outputs.ipynb)

---

## ✅ Checklist

Before running, confirm:
- [ ] Data file uploaded
- [ ] CPI data correct
- [ ] Sufficient runtime (about 5-10 minutes)
- [ ] Stable network connection

After running, check:
- [ ] All cells executed successfully (no red errors)
- [ ] Charts display correctly
- [ ] Result files downloaded

---

**Ready to start? Begin your analysis journey!** 🚀

Feel free to create issues on GitHub for any questions.
