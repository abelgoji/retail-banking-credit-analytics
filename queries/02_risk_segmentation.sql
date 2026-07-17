-- =============================================================================
-- 02_risk_segmentation.sql
-- Retail Banking Credit Risk & Loan Portfolio Analytics
--
-- Business question: where is credit risk actually concentrated? A blended
-- portfolio-wide charge-off rate hides where the real exposure sits -- this
-- breaks it down by risk grade, credit band, and product, and cross-tabs
-- risk grade against credit band to check whether internal risk grading is
-- doing its job.
-- =============================================================================

-- Charge-off and delinquency rate by risk grade
SELECT
    risk_grade,
    COUNT(*)                            AS loan_count,
    ROUND(SUM(current_balance), 2)      AS total_balance,
    ROUND(100.0 * SUM(CASE WHEN status = 'Charged Off' THEN 1 ELSE 0 END) / COUNT(*), 2) AS charge_off_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN delinquency_bucket IN ('60-89 DPD','90+ DPD') AND status = 'Active' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END), 0), 2) AS serious_delinquency_rate_pct
FROM loans
GROUP BY risk_grade
ORDER BY risk_grade;

-- Charge-off rate by customer credit band (joins to customers)
SELECT
    c.credit_band,
    COUNT(*)                            AS loan_count,
    ROUND(100.0 * SUM(CASE WHEN l.status = 'Charged Off' THEN 1 ELSE 0 END) / COUNT(*), 2) AS charge_off_rate_pct
FROM loans l
JOIN customers c ON c.customer_id = l.customer_id
GROUP BY c.credit_band
ORDER BY
    CASE c.credit_band WHEN 'Poor' THEN 1 WHEN 'Fair' THEN 2 WHEN 'Good' THEN 3 WHEN 'Excellent' THEN 4 END;

-- Risk grade x credit band cross-tab -- sanity check on internal grading
-- (a well-calibrated grading system should show risk grade tightening as
-- credit band improves; loans that don't follow the pattern are worth a
-- second look)
SELECT
    c.credit_band,
    l.risk_grade,
    COUNT(*) AS loan_count,
    ROUND(100.0 * COUNT(*) OVER (PARTITION BY c.credit_band) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM loans l
JOIN customers c ON c.customer_id = l.customer_id
GROUP BY c.credit_band, l.risk_grade
ORDER BY c.credit_band, l.risk_grade;

-- Risk-adjusted product mix: which product x risk-grade combinations carry
-- the most charged-off balance in dollar terms (not just rate) -- this is
-- what actually matters for provisioning
SELECT
    product_type,
    risk_grade,
    COUNT(*)                                                              AS loan_count,
    ROUND(SUM(CASE WHEN status = 'Charged Off' THEN current_balance ELSE 0 END), 2) AS charged_off_balance,
    RANK() OVER (ORDER BY SUM(CASE WHEN status = 'Charged Off' THEN current_balance ELSE 0 END) DESC) AS risk_rank
FROM loans
GROUP BY product_type, risk_grade
HAVING charged_off_balance > 0
ORDER BY charged_off_balance DESC
LIMIT 10;
