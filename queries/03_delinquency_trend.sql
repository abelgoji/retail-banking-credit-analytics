-- =============================================================================
-- 03_delinquency_trend.sql
-- Retail Banking Credit Risk & Loan Portfolio Analytics
--
-- Business question: is delinquency getting better or worse month over
-- month, and is it accelerating? A single current snapshot (query 01) can't
-- answer that -- this uses the payment history to build a monthly trend with
-- month-over-month change and a 3-month moving average to separate real
-- trend from noise.
-- =============================================================================

WITH monthly_stats AS (
    SELECT
        payment_month,
        COUNT(*)                                                        AS payments_due,
        ROUND(100.0 * SUM(CASE WHEN on_time_flag = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS late_rate_pct,
        ROUND(100.0 * SUM(CASE WHEN days_past_due >= 60 THEN 1 ELSE 0 END) / COUNT(*), 2) AS serious_delinquency_rate_pct
    FROM monthly_payments
    GROUP BY payment_month
)
SELECT
    payment_month,
    payments_due,
    late_rate_pct,
    serious_delinquency_rate_pct,
    -- month-over-month change in late rate
    ROUND(late_rate_pct - LAG(late_rate_pct) OVER (ORDER BY payment_month), 2) AS mom_change_pct_pts,
    -- 3-month moving average, smooths out single-month noise
    ROUND(AVG(late_rate_pct) OVER (ORDER BY payment_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS late_rate_3mo_avg
FROM monthly_stats
ORDER BY payment_month;

-- Same trend, broken out by risk grade, to see whether deterioration (if
-- any) is broad-based or concentrated in the riskier grades
SELECT
    l.risk_grade,
    mp.payment_month,
    ROUND(100.0 * SUM(CASE WHEN mp.on_time_flag = 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS late_rate_pct
FROM monthly_payments mp
JOIN loans l ON l.loan_id = mp.loan_id
GROUP BY l.risk_grade, mp.payment_month
ORDER BY l.risk_grade, mp.payment_month;
