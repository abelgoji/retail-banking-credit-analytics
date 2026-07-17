-- =============================================================================
-- 05_vintage_cohort_analysis.sql
-- Retail Banking Credit Risk & Loan Portfolio Analytics
--
-- Business question: is loan quality improving or deteriorating over time?
-- Comparing raw charge-off counts across cohorts is misleading because
-- older cohorts have had more time to default. This is a vintage analysis --
-- the standard credit risk technique -- that compares cohorts by months on
-- book instead of calendar time, plus a running cumulative default curve
-- per cohort.
-- =============================================================================

-- Vintage summary: default rate and average seasoning (months on book) by
-- origination quarter. Average months on book is included deliberately --
-- a young cohort with a low default rate hasn't been tested by time yet,
-- so the two columns have to be read together, not the default rate alone.
WITH loan_cohorts AS (
    SELECT
        loan_id,
        risk_grade,
        current_balance,
        status,
        months_on_book,
        (CAST(strftime('%Y', origination_date) AS INTEGER) || '-Q' ||
         ((CAST(strftime('%m', origination_date) AS INTEGER) - 1) / 3 + 1)) AS origination_quarter
    FROM loans
)
SELECT
    origination_quarter,
    COUNT(*)                                                                    AS cohort_size,
    ROUND(AVG(months_on_book), 1)                                               AS avg_months_on_book,
    ROUND(100.0 * SUM(CASE WHEN status = 'Charged Off' THEN 1 ELSE 0 END) / COUNT(*), 2) AS default_rate_pct
FROM loan_cohorts
GROUP BY origination_quarter
HAVING cohort_size >= 20
ORDER BY origination_quarter;

-- Cumulative default curve per cohort, month by month on book (the classic
-- vintage curve chart) -- running total of defaults divided by cohort size,
-- using a window function so the curve is computed directly in SQL.
-- Note: the source data captures a loan's current status at a single snapshot,
-- not the exact date it charged off, so each defaulted loan is attributed to
-- the months-on-book value observed today rather than its true default month.
-- This is a reasonable approximation for portfolio-level trend reading, but
-- would need default-date tracking to be precise enough for provisioning.
WITH loan_cohorts AS (
    SELECT
        loan_id,
        status,
        months_on_book,
        (CAST(strftime('%Y', origination_date) AS INTEGER) || '-Q' ||
         ((CAST(strftime('%m', origination_date) AS INTEGER) - 1) / 3 + 1)) AS origination_quarter
    FROM loans
),
cohort_sizes AS (
    SELECT origination_quarter, COUNT(*) AS cohort_size
    FROM loan_cohorts
    GROUP BY origination_quarter
    HAVING cohort_size >= 20
),
defaults_by_mob AS (
    SELECT
        lc.origination_quarter,
        lc.months_on_book,
        COUNT(*) AS defaults_at_this_mob
    FROM loan_cohorts lc
    JOIN cohort_sizes cs ON cs.origination_quarter = lc.origination_quarter
    WHERE lc.status = 'Charged Off'
    GROUP BY lc.origination_quarter, lc.months_on_book
)
SELECT
    d.origination_quarter,
    d.months_on_book,
    cs.cohort_size,
    SUM(d.defaults_at_this_mob) OVER (
        PARTITION BY d.origination_quarter ORDER BY d.months_on_book
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_defaults,
    ROUND(100.0 * SUM(d.defaults_at_this_mob) OVER (
        PARTITION BY d.origination_quarter ORDER BY d.months_on_book
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) / cs.cohort_size, 2) AS cumulative_default_rate_pct
FROM defaults_by_mob d
JOIN cohort_sizes cs ON cs.origination_quarter = d.origination_quarter
ORDER BY d.origination_quarter, d.months_on_book;
