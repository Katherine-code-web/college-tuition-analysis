-- Query 3: Institution Tier Segmentation by Admin Spending Share
--
-- Business purpose:
--   Segment institutions into three tiers based on their 2023 administrative
--   spending share (high / medium / low), then compare each tier's
--   instructional investment, total spending per student, and institution
--   type mix. This reveals whether high admin overhead correlates with
--   lower educational investment — a key question for affordability policy.
--
-- Table: spending
-- Key technique: NTILE() to compute dynamic tier thresholds, then CASE for labeling

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
