# Retail Banking Credit Risk & Loan Portfolio Analytics

Live dashboard: https://abelgoji.github.io/retail-banking-credit-analytics/

A SQL-first credit risk analytics project — portfolio composition, risk-grade segmentation, delinquency trend, deposit cross-sell targeting, and loan vintage/cohort analysis — built with hand-written SQL against a SQLite database, orchestrated with Python.

## Business Question

A retail bank's risk and portfolio management team doesn't need one blended charge-off number, they need to know where risk is actually concentrated, whether it's improving or just under-tested by time, and which customers represent the biggest untapped deposit relationship. This project answers all three directly in SQL, using the credit risk industry's own standard techniques (risk-grade segmentation, vintage/cohort analysis) rather than generic aggregation.

## Data & Methodology Note

**This dataset is synthetic, generated on purpose** (`src/generate_bank_data.py`) — not real loan or customer data from any institution. Loan-level consumer lending data isn't realistically available as a public dataset at usable size without violating privacy or licensing terms, so the data was built with deliberate, realistic credit risk logic instead:

- Default propensity is driven by risk grade (A–E) with a proper vintage/seasoning curve — younger loans have had less time to default, exactly like a real portfolio, not flat random chance
- Risk grade is correlated with, but not identical to, customer credit band, so the two don't move in lockstep (mirrors how real internal risk grading incorporates more than just credit score)
- Deposit account ownership is segment-correlated (Mass Market customers are meaningfully less likely to hold a deposit account than Private Banking customers), creating a genuine cross-sell signal to find

Fixed random seed (42), fully reproducible.

**One limitation stated directly**: the data captures each loan's status as of a single snapshot rather than an exact default date. The vintage curve analysis therefore attributes a charged-off loan's default to its current months-on-book value rather than the true month it defaulted — a reasonable approximation for trend-reading (which is what this project uses it for), not precise enough for actual loss provisioning. This tradeoff is documented in the SQL file itself (`queries/05_vintage_cohort_analysis.sql`).

## Data

5,000 customers, 6,280 loans across 4 products (Mortgage, Auto Loan, Credit Card, Personal Loan), $305.8M in current loan balance, 123,504 monthly payment records (24 months of history per active loan), $115.2M in deposit balances across 5,337 deposit accounts.

## Approach

- Generated a realistic, internally-consistent banking dataset in Python (`src/generate_bank_data.py`): customers, loans, monthly payment history, and deposit accounts, loaded into SQLite (`data/bank_data.db`).
- Answered five business questions directly in SQL (`queries/`): CTEs, window functions (`LAG`, running totals, moving averages, `RANK`, `NTILE`), and a full vintage/cohort analysis using the standard credit-risk technique of comparing cohorts by months-on-book rather than calendar time.
- `src/run_analysis.py` runs every query file against the database, saves each result to `data/results/`, and generates the charts used in the dashboard and this README.
- Results are presented in a single-file HTML dashboard (`index.html`) with an in-browser SQL query viewer.

## Key Findings

1. **The risk grading system is genuinely predictive, not just a label.** Charge-off rate rises 23x from Grade A (1.51%) to Grade E (35.37%), a far sharper and more monotonic signal than credit band alone (5.5x spread, Poor 19.81% to Excellent 3.61%). Pricing and provisioning decisions should weight risk grade more heavily than credit band on its own.
2. **The biggest cross-sell opportunity is concentrated in Mass Market, by volume.** 946 Mass Market customers hold an active loan with zero deposit relationship, more than 7x the combined loan-only count of Affluent and Private Banking combined. The segment's deposit-to-loan ratio (0.22) is less than a third of Affluent's (0.65) and an eighth of Private Banking's (1.91).
3. **Recent loan cohorts look safer only because they haven't been tested by time yet.** Average months-on-book falls from 53 months (2022-Q1 cohort) to 2.5 months (2026-Q2 cohort) in step with declining default rates in the raw data — a seasoning artifact, not evidence that recent underwriting is better. Cohorts need to season past roughly 24 months before their default rate can be trusted.
4. **Personal Loans quietly outperform secured products on credit quality.** Despite being unsecured, Personal Loans carry the lowest charge-off rate of all four products (6.52%), below both Auto Loans (8.49%) and Mortgages (9.51%) — worth investigating whether this reflects underwriting discipline or portfolio mix before assuming secured lending is automatically the safer book.

## Recommendation

Launch a deposit cross-sell campaign targeted first at the 946 Mass Market loan-only customers, using the `NTILE`-based outreach priority tiers already computed in `queries/04_crosssell_deposit_ratio.sql` to sequence contact by loan balance, highest first. On the risk side, treat 2025–2026 vintage performance as unproven rather than as evidence of improving underwriting until those cohorts pass the 24-month seasoning mark, and weight risk grade over credit band alone when setting pricing and loss provisions, since it's the sharper predictive signal of the two.

## Tech Stack

SQLite, SQL (CTEs, window functions, vintage/cohort analysis), Python (`pandas`, `numpy`, `matplotlib` — data generation and query orchestration only, no analysis logic lives in Python), HTML/CSS

## Repo Structure

```
retail-banking-credit-analytics/
├── README.md
├── index.html                          # https://abelgoji.github.io/retail-banking-credit-analytics/
├── requirements.txt
├── data/
│   ├── bank_data.db                    # SQLite database
│   ├── customers.csv / loans.csv / monthly_payments.csv / deposits.csv
│   └── results/                        # CSV output of every query
├── queries/
│   ├── 01_portfolio_overview.sql
│   ├── 02_risk_segmentation.sql
│   ├── 03_delinquency_trend.sql
│   ├── 04_crosssell_deposit_ratio.sql
│   └── 05_vintage_cohort_analysis.sql
├── charts/                             # PNG charts used in the dashboard/README
└── src/
    ├── generate_bank_data.py           # seeded, reproducible data generator
    └── run_analysis.py                 # runs every query file, saves results + charts
```

## Reproduce it

```
pip install -r requirements.txt
python src/generate_bank_data.py     # regenerates data/*.csv (seed=42)
python src/run_analysis.py           # rebuilds data/bank_data.db, data/results/, charts/
```

Then open `index.html` in a browser, no build step or server required.

## Credits

Built by Abel Williams Goji.
