"""
Synthetic retail banking dataset generator for the Retail Banking Credit Risk
& Loan Portfolio Analytics project.

This data is generated on purpose (not real bank or customer data) with
realistic business logic: risk-grade-correlated delinquency, seasonality,
loan vintage curves, and cross-sell patterns between loans and deposits.
Seeded and fully reproducible.
"""
import numpy as np
import pandas as pd
import json
from datetime import date, timedelta

SEED = 42
rng = np.random.default_rng(SEED)

N_CUSTOMERS = 5000
REGIONS = ["Northeast", "Midwest", "South", "West"]
SEGMENTS = ["Mass Market", "Affluent", "Private Banking"]
SEGMENT_WEIGHTS = [0.72, 0.23, 0.05]
CREDIT_BANDS = ["Poor", "Fair", "Good", "Excellent"]
CREDIT_BAND_WEIGHTS = [0.12, 0.28, 0.38, 0.22]
RISK_GRADES = ["A", "B", "C", "D", "E"]

RISK_GRADE_DEFAULT_PROPENSITY = {"A": 0.008, "B": 0.02, "C": 0.045, "D": 0.09, "E": 0.16}

PRODUCT_TYPES = ["Personal Loan", "Auto Loan", "Mortgage", "Credit Card"]
PRODUCT_WEIGHTS = [0.30, 0.27, 0.13, 0.30]
PRODUCT_PARAMS = {
    "Personal Loan": {"min_amt": 3000, "max_amt": 25000, "term_choices": [24, 36, 48], "rate_range": (0.09, 0.19)},
    "Auto Loan": {"min_amt": 8000, "max_amt": 45000, "term_choices": [36, 48, 60, 72], "rate_range": (0.05, 0.11)},
    "Mortgage": {"min_amt": 120000, "max_amt": 650000, "term_choices": [180, 240, 360], "rate_range": (0.045, 0.075)},
    "Credit Card": {"min_amt": 1000, "max_amt": 20000, "term_choices": [None], "rate_range": (0.16, 0.26)},
}

DEPOSIT_PRODUCTS = ["Checking", "Savings", "CD"]

TODAY = date(2026, 7, 1)
ORIGINATION_START = date(2022, 1, 1)
ORIGINATION_END = date(2026, 6, 1)


def month_range(start, end):
    months = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        months.append(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return months


ALL_MONTHS = month_range(ORIGINATION_START, TODAY)


def random_date_between(start, end):
    delta = (end - start).days
    return start + timedelta(days=int(rng.integers(0, max(delta, 1))))


# 1. Customers
customers = []
for cid in range(1, N_CUSTOMERS + 1):
    segment = rng.choice(SEGMENTS, p=SEGMENT_WEIGHTS)
    credit_band = rng.choice(CREDIT_BANDS, p=CREDIT_BAND_WEIGHTS)
    if segment == "Private Banking" and rng.random() < 0.6:
        credit_band = rng.choice(["Good", "Excellent"], p=[0.35, 0.65])
    elif segment == "Affluent" and rng.random() < 0.4:
        credit_band = rng.choice(["Good", "Excellent"], p=[0.5, 0.5])

    age = int(np.clip(rng.normal(44, 13), 21, 82))
    tenure_years = round(float(np.clip(rng.exponential(5.5), 0.2, 28)), 1)
    join_date = TODAY - timedelta(days=int(tenure_years * 365.25))
    income_bracket = rng.choice(
        ["<40k", "40k-75k", "75k-125k", "125k-200k", "200k+"],
        p=[0.14, 0.30, 0.32, 0.16, 0.08] if segment == "Mass Market" else
          ([0.02, 0.10, 0.28, 0.34, 0.26] if segment == "Affluent" else [0.0, 0.02, 0.10, 0.28, 0.60]),
    )
    customers.append({
        "customer_id": cid,
        "age": age,
        "income_bracket": income_bracket,
        "credit_band": credit_band,
        "region": rng.choice(REGIONS),
        "segment": segment,
        "tenure_years": tenure_years,
        "join_date": join_date.isoformat(),
    })
customers_df = pd.DataFrame(customers)

CREDIT_BAND_TO_RISK_GRADE_P = {
    "Poor":      [0.02, 0.08, 0.25, 0.40, 0.25],
    "Fair":      [0.05, 0.25, 0.40, 0.22, 0.08],
    "Good":      [0.25, 0.40, 0.25, 0.08, 0.02],
    "Excellent": [0.55, 0.32, 0.10, 0.02, 0.01],
}

# 2. Loans
loans = []
loan_id = 1
for _, cust in customers_df.iterrows():
    n_loans = rng.choice([0, 1, 2, 3], p=[0.18, 0.47, 0.27, 0.08])
    for _ in range(n_loans):
        product = rng.choice(PRODUCT_TYPES, p=PRODUCT_WEIGHTS)
        params = PRODUCT_PARAMS[product]
        risk_grade = rng.choice(RISK_GRADES, p=CREDIT_BAND_TO_RISK_GRADE_P[cust["credit_band"]])
        principal = float(rng.uniform(params["min_amt"], params["max_amt"]))
        term = rng.choice(params["term_choices"]) if params["term_choices"][0] is not None else None
        rate = float(rng.uniform(*params["rate_range"]))
        origination = random_date_between(ORIGINATION_START, ORIGINATION_END)
        months_on_book = max(1, (TODAY.year - origination.year) * 12 + (TODAY.month - origination.month))

        base_propensity = RISK_GRADE_DEFAULT_PROPENSITY[risk_grade]
        vintage_factor = 1 - np.exp(-months_on_book / 18)
        cum_default_prob = base_propensity * (1 + 2.2 * vintage_factor)
        is_defaulted = rng.random() < cum_default_prob and (term is None or months_on_book < (term or 999))

        if is_defaulted:
            status = "Charged Off"
            delinquency_bucket = "90+ DPD"
            current_balance = round(principal * float(rng.uniform(0.35, 0.95)), 2)
        else:
            paid_off = term is not None and months_on_book >= term
            if paid_off:
                status = "Paid Off"
                delinquency_bucket = "Current"
                current_balance = 0.0
            else:
                status = "Active"
                delinquency_bucket = rng.choice(
                    ["Current", "30-59 DPD", "60-89 DPD", "90+ DPD"],
                    p={
                        "A": [0.97, 0.02, 0.008, 0.002],
                        "B": [0.93, 0.05, 0.015, 0.005],
                        "C": [0.85, 0.09, 0.04, 0.02],
                        "D": [0.72, 0.14, 0.08, 0.06],
                        "E": [0.55, 0.20, 0.14, 0.11],
                    }[risk_grade],
                )
                if term is not None:
                    pct_remaining = max(0.05, 1 - (months_on_book / term))
                    current_balance = round(principal * pct_remaining * float(rng.uniform(0.9, 1.05)), 2)
                else:
                    current_balance = round(principal * float(rng.uniform(0.1, 0.85)), 2)

        loans.append({
            "loan_id": loan_id,
            "customer_id": cust["customer_id"],
            "product_type": product,
            "origination_date": origination.isoformat(),
            "principal_amount": round(principal, 2),
            "interest_rate": round(rate, 4),
            "term_months": term,
            "risk_grade": risk_grade,
            "current_balance": current_balance,
            "delinquency_bucket": delinquency_bucket,
            "status": status,
            "months_on_book": months_on_book,
        })
        loan_id += 1

loans_df = pd.DataFrame(loans)

# 3. Monthly payments
payments = []
payment_id = 1
for _, loan in loans_df.iterrows():
    origination = date.fromisoformat(loan["origination_date"])
    months = month_range(origination, TODAY)
    months = months[-24:]
    scheduled = round((loan["principal_amount"] / (loan["term_months"] or 24)) * (1 + loan["interest_rate"] / 12), 2)
    risk_grade = loan["risk_grade"]
    late_prob_by_grade = {"A": 0.02, "B": 0.05, "C": 0.11, "D": 0.20, "E": 0.32}[risk_grade]
    for m in months:
        is_late = rng.random() < late_prob_by_grade
        days_past_due = int(rng.choice([15, 30, 45, 60, 90], p=[0.35, 0.30, 0.15, 0.12, 0.08])) if is_late else 0
        actual_payment = 0.0 if days_past_due >= 60 else scheduled
        payments.append({
            "payment_id": payment_id,
            "loan_id": loan["loan_id"],
            "payment_month": m.isoformat(),
            "scheduled_payment": scheduled,
            "actual_payment": actual_payment,
            "days_past_due": days_past_due,
            "on_time_flag": 0 if is_late else 1,
        })
        payment_id += 1

payments_df = pd.DataFrame(payments)

# 4. Deposits
deposits = []
deposit_id = 1
for _, cust in customers_df.iterrows():
    has_deposit = rng.random() < (0.62 if cust["segment"] == "Mass Market" else 0.85)
    if not has_deposit:
        continue
    n_products = rng.choice([1, 2, 3], p=[0.55, 0.35, 0.10])
    chosen = rng.choice(DEPOSIT_PRODUCTS, size=n_products, replace=False)
    for prod in chosen:
        if prod == "Checking":
            balance = float(rng.gamma(2.0, 2200))
        elif prod == "Savings":
            balance = float(rng.gamma(2.2, 5200))
        else:
            balance = float(rng.gamma(2.5, 9000))
        if cust["segment"] == "Affluent":
            balance *= 2.3
        elif cust["segment"] == "Private Banking":
            balance *= 6.0
        opened = random_date_between(date.fromisoformat(cust["join_date"]), TODAY)
        deposits.append({
            "deposit_id": deposit_id,
            "customer_id": cust["customer_id"],
            "product_type": prod,
            "balance": round(balance, 2),
            "opened_date": opened.isoformat(),
        })
        deposit_id += 1

deposits_df = pd.DataFrame(deposits)

customers_df.to_csv("data/customers.csv", index=False)
loans_df.to_csv("data/loans.csv", index=False)
payments_df.to_csv("data/monthly_payments.csv", index=False)
deposits_df.to_csv("data/deposits.csv", index=False)

summary = {
    "n_customers": len(customers_df),
    "n_loans": len(loans_df),
    "n_payments": len(payments_df),
    "n_deposits": len(deposits_df),
    "total_loan_principal": round(loans_df["principal_amount"].sum(), 2),
    "total_current_balance": round(loans_df["current_balance"].sum(), 2),
    "total_deposit_balance": round(deposits_df["balance"].sum(), 2),
    "charge_off_rate_pct": round((loans_df["status"] == "Charged Off").mean() * 100, 2),
}
print(json.dumps(summary, indent=2))
