"""
SQL Data Pipeline — U.S. Higher Education Spending Analysis (2018-2023)
=======================================================================

Loads IPEDS panel data into a SQLite database and runs three analytical
queries that surface actionable business insights:

  1. State-level ranking of admin vs. instructional spending growth gap
  2. Year-over-year spending changes per institution (window functions)
  3. Institution tier segmentation by admin spending share

Results are exported to the outputs/ directory as CSV files.

Author: Yun-Ting Su
Data Source: IPEDS (Integrated Postsecondary Education Data System)
"""

import os
import sqlite3
import pandas as pd

# ============================================================================
# Configuration
# ============================================================================

INPUT_FILE = 'data/panel_2018_2023.csv'
DB_PATH = 'spending_analysis.db'
OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# Database Setup
# ============================================================================

def load_data_to_sqlite(csv_path: str, db_path: str) -> sqlite3.Connection:
    """
    Load the IPEDS panel CSV into a SQLite database.

    Creates a `spending` table with appropriate column types. Replaces
    any existing table so the pipeline is idempotent.

    Parameters
    ----------
    csv_path : str
        Path to the input CSV file.
    db_path : str
        Path for the SQLite database file.

    Returns
    -------
    conn : sqlite3.Connection
        Open connection to the loaded database.
    """
    print("=" * 70)
    print("Loading data into SQLite database...")
    print("=" * 70)

    df = pd.read_csv(csv_path)
    print(f"  Rows loaded: {len(df):,}")
    print(f"  Columns: {list(df.columns)}")

    conn = sqlite3.connect(db_path)

    # Write to SQLite with explicit type mapping
    df.to_sql(
        'spending',
        conn,
        if_exists='replace',
        index=False,
        dtype={
            'UNITID':           'INTEGER',
            'year':             'INTEGER',
            'state':            'REAL',
            'instruction':      'REAL',
            'research':         'REAL',
            'public_svc':       'REAL',
            'student_svc':      'REAL',
            'admin':            'REAL',
            'ops':              'REAL',
            'total':            'REAL',
            'fte':              'REAL',
            'type':             'TEXT',
            'INSTNM':           'TEXT',
            'STABBR':           'TEXT',
            'CONTROL':          'INTEGER',
            'OBEREG':           'INTEGER',
            'admin_pct':        'REAL',
            'instruction_pct':  'REAL',
            'research_pct':     'REAL',
            'admin_per_fte':    'REAL',
            'instruction_per_fte': 'REAL',
            'state_per_fte':    'REAL',
            'total_per_fte':    'REAL',
        }
    )

    # Add indexes for query performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_year      ON spending(year);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_state     ON spending(STABBR);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_unitid    ON spending(UNITID);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_type      ON spending(type);")
    conn.commit()

    print(f"  Database ready: {db_path}\n")
    return conn


# ============================================================================
# Query 1: State Ranking — Admin vs. Instruction Spending Growth Gap
# ============================================================================

QUERY_1 = """
-- Business purpose:
--   Identify which states show the largest divergence between administrative
--   and instructional spending growth from 2018 to 2023.
--   States with a large positive gap (admin growing faster than instruction)
--   signal a potential efficiency or governance concern.

WITH base AS (
    SELECT
        STABBR                      AS state,
        AVG(admin_pct)              AS avg_admin_pct,
        AVG(instruction_pct)        AS avg_instruction_pct
    FROM spending
    WHERE year = 2018
    GROUP BY STABBR
),
end_year AS (
    SELECT
        STABBR                      AS state,
        AVG(admin_pct)              AS avg_admin_pct,
        AVG(instruction_pct)        AS avg_instruction_pct
    FROM spending
    WHERE year = 2023
    GROUP BY STABBR
),
changes AS (
    SELECT
        b.state,
        ROUND((e.avg_admin_pct - b.avg_admin_pct) * 100, 4)       AS admin_pct_change,
        ROUND((e.avg_instruction_pct - b.avg_instruction_pct) * 100, 4) AS instruction_pct_change,
        ROUND(
            ((e.avg_admin_pct - b.avg_admin_pct)
             - (e.avg_instruction_pct - b.avg_instruction_pct)) * 100,
            4
        )                                                           AS spending_gap
    FROM base b
    JOIN end_year e ON b.state = e.state
)
SELECT
    state,
    admin_pct_change,
    instruction_pct_change,
    spending_gap,
    RANK() OVER (ORDER BY spending_gap DESC) AS gap_rank
FROM changes
ORDER BY gap_rank;
"""


def run_query_1(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Run Query 1: rank states by admin vs. instructional spending growth gap.

    A positive spending_gap means admin costs grew faster than instruction
    in that state — a signal of budget misalignment.

    Returns the result as a DataFrame and saves it to outputs/.
    """
    print("=" * 70)
    print("Query 1: State Spending Gap Ranking")
    print("=" * 70)
    print("Business question: Which states show admin costs growing fastest")
    print("relative to instructional spending (2018 -> 2023)?\n")

    df = pd.read_sql_query(QUERY_1, conn)

    print(df.to_string(index=False))

    out_path = os.path.join(OUTPUT_DIR, 'query1_state_spending_gap.csv')
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}\n")
    return df


# ============================================================================
# Query 2: Year-over-Year Spending Changes Per Institution (Window Functions)
# ============================================================================

QUERY_2 = """
-- Business purpose:
--   Calculate year-over-year percentage changes in admin and instructional
--   spending for every institution. Window functions (LAG) allow us to
--   compare each row to the prior year within the same institution,
--   without collapsing the data — preserving institution-level granularity
--   for downstream segmentation or flagging.

SELECT
    UNITID,
    INSTNM,
    STABBR,
    type,
    year,
    ROUND(admin_per_fte, 2)             AS admin_per_fte,
    ROUND(instruction_per_fte, 2)       AS instruction_per_fte,

    -- Year-over-year admin per FTE change (%)
    ROUND(
        (admin_per_fte
         - LAG(admin_per_fte) OVER (PARTITION BY UNITID ORDER BY year))
        / NULLIF(LAG(admin_per_fte) OVER (PARTITION BY UNITID ORDER BY year), 0)
        * 100,
        2
    )                                   AS admin_yoy_pct,

    -- Year-over-year instruction per FTE change (%)
    ROUND(
        (instruction_per_fte
         - LAG(instruction_per_fte) OVER (PARTITION BY UNITID ORDER BY year))
        / NULLIF(LAG(instruction_per_fte) OVER (PARTITION BY UNITID ORDER BY year), 0)
        * 100,
        2
    )                                   AS instruction_yoy_pct,

    -- Cumulative admin per FTE change vs. 2018 baseline (%)
    ROUND(
        (admin_per_fte
         - FIRST_VALUE(admin_per_fte) OVER (PARTITION BY UNITID ORDER BY year))
        / NULLIF(FIRST_VALUE(admin_per_fte) OVER (PARTITION BY UNITID ORDER BY year), 0)
        * 100,
        2
    )                                   AS admin_cumulative_pct

FROM spending
WHERE admin_per_fte IS NOT NULL
  AND instruction_per_fte IS NOT NULL
ORDER BY UNITID, year;
"""


def run_query_2(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Run Query 2: year-over-year spending changes per institution using window functions.

    LAG() compares each year's spending to the prior year within the same
    institution. FIRST_VALUE() tracks cumulative drift from the 2018 baseline.

    Returns the result as a DataFrame and saves it to outputs/.
    """
    print("=" * 70)
    print("Query 2: Year-over-Year Spending Changes per Institution")
    print("=" * 70)
    print("Business question: How does each institution's spending evolve")
    print("year-by-year, and how far has it drifted from its 2018 baseline?\n")

    df = pd.read_sql_query(QUERY_2, conn)

    print(f"  Rows returned: {len(df):,}")
    print("\nSample (first 10 rows):")
    print(df.head(10).to_string(index=False))

    out_path = os.path.join(OUTPUT_DIR, 'query2_yoy_spending_changes.csv')
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}\n")
    return df


# ============================================================================
# Query 3: Institution Tier Segmentation by Admin Spending Share
# ============================================================================

QUERY_3 = """
-- Business purpose:
--   Segment institutions into three tiers based on their 2023 administrative
--   spending share (high / medium / low), then compare each tier's
--   instructional investment, total spending per student, and institution
--   type mix. This reveals whether high admin overhead correlates with
--   lower educational investment — a key question for affordability policy.

WITH latest AS (
    SELECT *
    FROM spending
    WHERE year = 2023
),
tier_thresholds AS (
    -- Compute 33rd and 67th percentile cutoffs for admin_pct in 2023
    SELECT
        admin_pct,
        NTILE(3) OVER (ORDER BY admin_pct) AS ntile_group
    FROM latest
    WHERE admin_pct IS NOT NULL
),
cutoffs AS (
    SELECT
        MAX(CASE WHEN ntile_group = 1 THEN admin_pct END) AS p33,
        MAX(CASE WHEN ntile_group = 2 THEN admin_pct END) AS p67
    FROM tier_thresholds
),
tiered AS (
    SELECT
        l.*,
        CASE
            WHEN l.admin_pct <= c.p33 THEN 'Low Admin'
            WHEN l.admin_pct <= c.p67 THEN 'Medium Admin'
            ELSE 'High Admin'
        END AS admin_tier
    FROM latest l
    CROSS JOIN cutoffs c
    WHERE l.admin_pct IS NOT NULL
)
SELECT
    admin_tier,
    COUNT(*)                                            AS institution_count,
    ROUND(AVG(admin_pct) * 100, 2)                     AS avg_admin_pct,
    ROUND(AVG(instruction_pct) * 100, 2)               AS avg_instruction_pct,
    ROUND(AVG(total_per_fte), 0)                        AS avg_total_per_fte,
    ROUND(AVG(instruction_per_fte), 0)                  AS avg_instruction_per_fte,
    SUM(CASE WHEN type = 'Public' THEN 1 ELSE 0 END)   AS public_count,
    SUM(CASE WHEN type = 'Private' THEN 1 ELSE 0 END)  AS private_count
FROM tiered
GROUP BY admin_tier
ORDER BY avg_admin_pct;
"""


def run_query_3(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Run Query 3: segment institutions into tiers by admin spending share,
    then compare instruction investment and institution type mix across tiers.

    A strong inverse relationship between admin tier and instruction spending
    would confirm that administrative overhead crowds out teaching resources.

    Returns the result as a DataFrame and saves it to outputs/.
    """
    print("=" * 70)
    print("Query 3: Institution Tier Analysis by Admin Spending")
    print("=" * 70)
    print("Business question: Do high-admin institutions systematically spend")
    print("less on instruction? How does institution type (public/private)")
    print("distribute across tiers?\n")

    df = pd.read_sql_query(QUERY_3, conn)

    print(df.to_string(index=False))

    out_path = os.path.join(OUTPUT_DIR, 'query3_institution_tier_analysis.csv')
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}\n")
    return df


# ============================================================================
# Main
# ============================================================================

def main():
    """Run the full SQL data pipeline."""
    print("\n" + "=" * 70)
    print("SQL Data Pipeline — U.S. Higher Education Spending Analysis")
    print("=" * 70 + "\n")

    # Load data
    conn = load_data_to_sqlite(INPUT_FILE, DB_PATH)

    # Run analytical queries
    df1 = run_query_1(conn)
    df2 = run_query_2(conn)
    df3 = run_query_3(conn)

    conn.close()

    print("=" * 70)
    print("Pipeline complete. Output files:")
    print(f"  outputs/query1_state_spending_gap.csv     ({len(df1)} rows)")
    print(f"  outputs/query2_yoy_spending_changes.csv   ({len(df2)} rows)")
    print(f"  outputs/query3_institution_tier_analysis.csv ({len(df3)} rows)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
