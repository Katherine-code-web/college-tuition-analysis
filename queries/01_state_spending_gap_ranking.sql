-- Query 1: State Ranking — Admin vs. Instructional Spending Growth Gap (2018-2023)
--
-- Business purpose:
--   Identify which states show the largest divergence between administrative
--   and instructional spending growth from 2018 to 2023.
--   States with a large positive gap (admin growing faster than instruction)
--   signal a potential efficiency or governance concern.
--
-- Table: spending
-- Output: state, admin_pct_change, instruction_pct_change, spending_gap, gap_rank

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
        ROUND((e.avg_admin_pct - b.avg_admin_pct) * 100, 4)            AS admin_pct_change,
        ROUND((e.avg_instruction_pct - b.avg_instruction_pct) * 100, 4) AS instruction_pct_change,
        ROUND(
            ((e.avg_admin_pct - b.avg_admin_pct)
             - (e.avg_instruction_pct - b.avg_instruction_pct)) * 100,
            4
        )                                                                AS spending_gap
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
