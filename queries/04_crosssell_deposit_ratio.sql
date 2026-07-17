-- =============================================================================
-- 04_crosssell_deposit_ratio.sql
-- Retail Banking Credit Risk & Loan Portfolio Analytics
--
-- Business question: which customers are loan-only (no deposit relationship)
-- and represent a cross-sell opportunity, and how does the deposit-to-loan
-- ratio vary by segment? A bank funding its loan book primarily through
-- borrowed money rather than its own deposit base is a liquidity signal
-- worth watching at the segment level.
-- =============================================================================

WITH customer_loans AS (
    SELECT customer_id, SUM(current_balance) AS total_loan_balance, COUNT(*) AS loan_count
    FROM loans
    WHERE status = 'Active'
    GROUP BY customer_id
),
customer_deposits AS (
    SELECT customer_id, SUM(balance) AS total_deposit_balance, COUNT(*) AS deposit_count
    FROM deposits
    GROUP BY customer_id
)
SELECT
    c.segment,
    COUNT(DISTINCT c.customer_id)                                              AS total_customers,
    COUNT(DISTINCT cl.customer_id)                                             AS customers_with_active_loan,
    COUNT(DISTINCT cd.customer_id)                                             AS customers_with_deposit,
    SUM(CASE WHEN cl.customer_id IS NOT NULL AND cd.customer_id IS NULL THEN 1 ELSE 0 END) AS loan_only_no_deposit,
    ROUND(100.0 * SUM(CASE WHEN cl.customer_id IS NOT NULL AND cd.customer_id IS NULL THEN 1 ELSE 0 END)
          / NULLIF(COUNT(DISTINCT cl.customer_id), 0), 2)                     AS pct_loan_customers_no_deposit,
    ROUND(SUM(COALESCE(cd.total_deposit_balance, 0)), 2)                      AS segment_deposit_balance,
    ROUND(SUM(COALESCE(cl.total_loan_balance, 0)), 2)                         AS segment_loan_balance,
    ROUND(SUM(COALESCE(cd.total_deposit_balance, 0)) / NULLIF(SUM(COALESCE(cl.total_loan_balance, 0)), 0), 2) AS deposit_to_loan_ratio
FROM customers c
LEFT JOIN customer_loans cl ON cl.customer_id = c.customer_id
LEFT JOIN customer_deposits cd ON cd.customer_id = c.customer_id
GROUP BY c.segment
ORDER BY deposit_to_loan_ratio ASC;

-- Rank individual loan-only customers by loan balance -- the highest-value,
-- highest-priority cross-sell targets (largest loan exposure, zero deposit
-- relationship), using NTILE to bucket them into outreach priority tiers
WITH customer_loans AS (
    SELECT customer_id, SUM(current_balance) AS total_loan_balance
    FROM loans
    WHERE status = 'Active'
    GROUP BY customer_id
),
customer_deposits AS (
    SELECT DISTINCT customer_id FROM deposits
)
SELECT
    cl.customer_id,
    c.segment,
    c.credit_band,
    cl.total_loan_balance,
    NTILE(4) OVER (ORDER BY cl.total_loan_balance DESC) AS outreach_priority_tier -- 1 = highest priority
FROM customer_loans cl
JOIN customers c ON c.customer_id = cl.customer_id
LEFT JOIN customer_deposits cd ON cd.customer_id = cl.customer_id
WHERE cd.customer_id IS NULL
ORDER BY cl.total_loan_balance DESC
LIMIT 25;
