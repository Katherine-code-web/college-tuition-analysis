-- Query 2: Year-over-Year Spending Changes Per Institution (Window Functions)
--
-- Business purpose:
--   Calculate year-over-year percentage changes in admin and instructional
--   spending for every institution. Window functions (LAG) allow us to
--   compare each row to the prior year within the same institution,
--   without collapsing the data — preserving institution-level granularity
--   for downstream segmentation or flagging.
--
-- Table: spending
-- Key window functions: LAG() for YoY change, FIRST_VALUE() for cumulative drift

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
