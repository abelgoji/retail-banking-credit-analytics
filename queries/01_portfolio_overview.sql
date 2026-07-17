-- =============================================================================
-- 01_portfolio_overview.sql
-- Retail Banking Credit Risk & Loan Portfolio Analytics
--
-- Business question: what does the loan portfolio look like today, in total
-- and by product? This is the starting point every other query in this repo
-- builds on -- size, composition, and overall portfolio health.
-- =============================================================================

-- Portfolio-wide headline numbers
SELECT
    COUNT(*)                                            AS total_loans,
    ROUND(SUM(principal_amount), 2)                     AS total_principal_originated,
    ROUND(SUM(current_balance), 2)                       AS total_current_balance,
    ROUND(SUM(CASE WHEN status = 'Charged Off' THEN current_balance ELSE 0 END), 2) AS charged_off_balance,
    ROUND(100.0 * SUM(CASE WHEN status = 'Charged Off' THEN 1 ELSE 0 END) / COUNT(*), 2) AS charge_off_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN delinquency_bucket != 'Current' AND status = 'Active' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END), 0), 2) AS active_delinquency_rate_pct
FROM loans;

-- Portfolio composition by product type
SELECT
    product_type,
    COUNT(*)                                    AS loan_count,
    ROUND(SUM(current_balance), 2)              AS total_current_balance,
    ROUND(AVG(current_balance), 2)              AS avg_current_balance,
    ROUND(AVG(interest_rate) * 100, 2)          AS avg_interest_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'Charged Off' THEN 1 ELSE 0 END) / COUNT(*), 2) AS charge_off_rate_pct
FROM loans
GROUP BY product_type
ORDER BY total_current_balance DESC;

-- Loan status breakdown (Active / Paid Off / Charged Off)
SELECT
    status,
    COUNT(*)                        AS loan_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM loans), 2) AS pct_of_portfolio,
    ROUND(SUM(current_balance), 2)  AS total_current_balance
FROM loans
GROUP BY status
ORDER BY loan_count DESC;

-- Delinquency bucket breakdown, active loans only
SELECT
    delinquency_bucket,
    COUNT(*)                        AS loan_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM loans WHERE status = 'Active'), 2) AS pct_of_active_loans,
    ROUND(SUM(current_balance), 2)  AS balance_in_bucket
FROM loans
WHERE status = 'Active'
GROUP BY delinquency_bucket
ORDER BY
    CASE delinquency_bucket
        WHEN 'Current' THEN 1
        WHEN '30-59 DPD' THEN 2
        WHEN '60-89 DPD' THEN 3
        WHEN '90+ DPD' THEN 4
    END;
