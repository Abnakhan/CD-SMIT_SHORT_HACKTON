import pandas as pd

print("Loading data files for monthly summary...")
df_emp = pd.read_csv("employees_cleaned.csv")
df_history = pd.read_csv("employment_history.csv")
df_attendance = pd.read_csv("daily_attendance_with_ot.csv")
df_ot_req = pd.read_csv("overtime_requests.csv")
df_payroll = pd.read_csv("payroll_lines.csv")

# Date conversions
df_history["effective_from"] = pd.to_datetime(
    df_history["effective_from"], format="mixed", errors="coerce"
)
df_history["effective_to"] = pd.to_datetime(
    df_history["effective_to"], format="mixed", errors="coerce"
)
df_attendance["date"] = pd.to_datetime(
    df_attendance["date"], format="mixed", errors="coerce"
)

# 1. Month-end Dates Define Karein (April 2026 to September 2026)
month_ends = pd.date_range(start="2026-04-01", end="2026-09-30", freq="ME")

summary_records = []

for m_end in month_ends:
    m_str = m_end.strftime("%Y-%m")
    print(f"Processing month: {m_str}...")

    # Rule 4: Headcount eligibility at month end
    # hire_date <= month_end and (separation_date is NaN or separation_date >= month_end)
    df_emp["hire_date"] = pd.to_datetime(
        df_emp["hire_date"], format="mixed", errors="coerce"
    )
    df_emp["separation_date"] = pd.to_datetime(
        df_emp["separation_date"], format="mixed", errors="coerce"
    )

    active_emp = df_emp[
        (df_emp["hire_date"] <= m_end)
        & (
            df_emp["separation_date"].isna()
            | (df_emp["separation_date"] >= m_end)
        )
    ].copy()

    # Rule 3: Find department on the last day of the month using employment_history
    # Let's map department from employment history where effective_from <= m_end
    # Sort history by effective_from descending and drop duplicates per emp_id to get latest active record up to m_end
    valid_hist = df_history[df_history["effective_from"] <= m_end].sort_values(
        by=["emp_id", "effective_from"], ascending=[True, False]
    )
    latest_hist = valid_hist.drop_duplicates(subset=["emp_id"]).copy()

    # Merge department info
    active_emp = pd.merge(
        active_emp,
        latest_hist[["emp_id", "dept_id", "grade", "basic_salary"]],
        on="emp_id",
        how="left",
    )

    headcount_count = len(active_emp)

    # 2. Payroll Aggregation for the month (Rule 21)
    m_payroll = df_payroll[df_payroll["payroll_month"] == m_str]

    # Earnings sum
    total_earnings = m_payroll[
        m_payroll["component_type"].str.upper() == "EARNING"
    ]["amount"].sum()

    # Deductions sum (positive amounts)
    total_deductions = m_payroll[
        m_payroll["component_type"].str.upper() == "DEDUCTION"
    ]["amount"].sum()

    # Overtime paid units from payroll
    ot_units_paid = m_payroll[
        m_payroll["component"].str.upper() == "OVERTIME"
    ]["units"].sum()

    summary_records.append(
        {
            "payroll_month": m_str,
            "headcount": headcount_count,
            "total_earnings_pkr": total_earnings,
            "total_deductions_pkr": total_deductions,
            "ot_hours_paid": ot_units_paid,
        }
    )

# Create summary dataframe
df_summary = pd.DataFrame(summary_records)

# Save to CSV
df_summary.to_csv("monthly_hr_payroll_summary.csv", index=False)
print(
    "\nPart 5 complete! Monthly summary saved to 'monthly_hr_payroll_summary.csv'."
)
print("\n--- Monthly Summary Preview ---")
print(df_summary)