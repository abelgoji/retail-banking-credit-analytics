"""
Runs every SQL file in queries/ against the SQLite database built from the
generated CSVs, saves each statement's result to data/results/, and produces
a handful of summary charts. Mirrors the structure of the retail-sql-analytics
project's run_analysis.py.
"""
import sqlite3
import re
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

DB_PATH = "data/bank_data.db"
QUERY_DIR = Path("queries")
RESULTS_DIR = Path("data/results")
CHARTS_DIR = Path("charts")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


def strip_sql_comments(sql_text):
    lines = [l for l in sql_text.splitlines() if not l.strip().startswith("--")]
    return "\n".join(lines)


def run_query_file(conn, path):
    raw = path.read_text()
    cleaned = strip_sql_comments(raw)
    statements = [s.strip() for s in cleaned.split(";") if s.strip()]
    results = []
    for i, stmt in enumerate(statements):
        df = pd.read_sql_query(stmt, conn)
        results.append(df)
        suffix = f"_{i + 1}" if len(statements) > 1 else ""
        out_path = RESULTS_DIR / f"{path.stem}{suffix}.csv"
        df.to_csv(out_path, index=False)
    return results


def main():
    conn = sqlite3.connect(DB_PATH)
    all_results = {}
    for path in sorted(QUERY_DIR.glob("*.sql")):
        print(f"Running {path.name} ...")
        all_results[path.stem] = run_query_file(conn, path)

    # ---- Charts -------------------------------------------------------
    plt.style.use("seaborn-v0_8-whitegrid")

    # Chart 1: charge-off rate by risk grade
    df = all_results["02_risk_segmentation"][0]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(df["risk_grade"], df["charge_off_rate_pct"], color="#6366f1")
    ax.set_title("Charge-off Rate by Risk Grade")
    ax.set_ylabel("Charge-off rate (%)")
    ax.set_xlabel("Risk grade")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "01_chargeoff_by_risk_grade.png", dpi=150)
    plt.close(fig)

    # Chart 2: portfolio composition by product (current balance)
    df = all_results["01_portfolio_overview"][1]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.pie(df["total_current_balance"], labels=df["product_type"], autopct="%1.0f%%",
           colors=["#6366f1", "#8b5cf6", "#10b981", "#f59e0b"])
    ax.set_title("Loan Portfolio Composition by Product (Current Balance)")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "02_portfolio_composition.png", dpi=150)
    plt.close(fig)

    # Chart 3: delinquency trend over time (3-month moving average)
    df = all_results["03_delinquency_trend"][0]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(df["payment_month"], df["late_rate_pct"], label="Monthly late rate", color="#c7c7f5", linewidth=1)
    ax.plot(df["payment_month"], df["late_rate_3mo_avg"], label="3-month moving average", color="#6366f1", linewidth=2.5)
    ax.set_title("Portfolio Late Payment Rate Over Time")
    ax.set_ylabel("Late rate (%)")
    ax.tick_params(axis="x", rotation=90, labelsize=6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "03_delinquency_trend.png", dpi=150)
    plt.close(fig)

    # Chart 4: vintage cumulative default curves
    df = all_results["05_vintage_cohort_analysis"][1]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for cohort, sub in df.groupby("origination_quarter"):
        ax.plot(sub["months_on_book"], sub["cumulative_default_rate_pct"], marker="o", markersize=3, label=cohort)
    ax.set_title("Cumulative Default Rate by Loan Vintage (Months on Book)")
    ax.set_xlabel("Months on book")
    ax.set_ylabel("Cumulative default rate (%)")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "04_vintage_curves.png", dpi=150)
    plt.close(fig)

    conn.close()
    print("Done. Results in data/results/, charts in charts/.")


if __name__ == "__main__":
    main()
