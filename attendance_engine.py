import json
import pandas as pd

print("Loading cleaned data and reference files...")
df_emp = pd.read_csv("employees_cleaned.csv")
df_punches = pd.read_csv("biometric_punches_cleaned.csv")
df_roster = pd.read_csv("shift_roster.csv")
df_holidays = pd.read_csv("holidays.csv")

with open("shifts.json", "r") as f:
    shifts_data = json.load(f)

with open("leave_requests.json", "r") as f:
    leave_requests = json.load(f)

# Dates formatting with mixed format handling
df_punches["punch_time"] = pd.to_datetime(
    df_punches["punch_time"], format="mixed", errors="coerce"
)
df_holidays["holiday_date"] = pd.to_datetime(
    df_holidays["holiday_date"], format="mixed", errors="coerce"
)
df_emp["hire_date"] = pd.to_datetime(
    df_emp["hire_date"], format="mixed", errors="coerce"
)
df_emp["separation_date"] = pd.to_datetime(
    df_emp["separation_date"], format="mixed", errors="coerce"
)

# 1. Date Range Create Karein (1 April 2026 se 30 September 2026 tak)
date_range = pd.date_range(start="2026-04-01", end="2026-09-30")

# Har employee ke liye poori date range ka Cartesian product (Grid) banana (Columns shamil hain)
emp_list = df_emp[[
    "emp_id",
    "plant",
    "department",
    "employment_type",
    "hire_date",
    "separation_date",
]].copy()
full_grid = []

for _, emp in emp_list.iterrows():
    h_date = emp["hire_date"]
    s_date = (
        emp["separation_date"]
        if pd.notna(emp["separation_date"])
        else pd.Timestamp("2026-09-30")
    )

    if pd.isna(h_date):
        continue

    active_dates = date_range[
        (date_range >= h_date) & (date_range <= s_date)
    ]
    for d in active_dates:
        full_grid.append(
            {
                "emp_id": emp["emp_id"],
                "plant": emp["plant"],
                "department": emp["department"],
                "date": d,
            }
        )

df_grid = pd.DataFrame(full_grid)

# 2. Shift Roster & Forward Fill (Rule 6)
df_roster["week_start"] = pd.to_datetime(
    df_roster["week_start"], format="mixed", errors="coerce"
)
df_grid["week_start"] = df_grid["date"] - pd.to_timedelta(
    df_grid["date"].dt.weekday, unit="d"
)

df_grid = pd.merge(
    df_grid,
    df_roster,
    on=["emp_id", "week_start"],
    how="left",
)
df_grid["shift_code"] = (
    df_grid.groupby("emp_id")["shift_code"]
    .ffill()
    .bfill()
    .fillna("GEN")
)

# 3. Daily First & Last Punch
df_punches["date"] = df_punches["punch_time"].dt.date
df_punches["date"] = pd.to_datetime(df_punches["date"])

daily_punches = (
    df_punches.groupby(["emp_id", "date"])["punch_time"]
    .agg(check_in="min", check_out="max", punch_count="count")
    .reset_index()
)

df_master = pd.merge(df_grid, daily_punches, on=["emp_id", "date"], how="left")
df_master["punch_count"] = df_master["punch_count"].fillna(0)

# 4. Leave Requests Processing
approved_leaves = []
for req in leave_requests:
    approvals = req.get("approvals", [])
    manager_app = any(
        a.get("approver_role") == "Manager" and a.get("action") == "Approved"
        for a in approvals
    )
    hr_app = any(
        a.get("approver_role") == "HR" and a.get("action") == "Approved"
        for a in approvals
    )
    cancelled = req.get("cancelled_at")

    if manager_app and hr_app and not cancelled:
        emp_id = req["employee"]["emp_id"]
        start_d = pd.to_datetime(
            req["leave"]["from"], format="mixed", errors="coerce"
        )
        end_d = pd.to_datetime(
            req["leave"]["to"], format="mixed", errors="coerce"
        )
        if pd.notna(start_d) and pd.notna(end_d):
            for single_date in pd.date_range(start_d, end_d):
                approved_leaves.append({"emp_id": emp_id, "date": single_date})

df_leaves = pd.DataFrame(approved_leaves)
if not df_leaves.empty:
    df_leaves["is_leave"] = True
    df_master = pd.merge(
        df_master, df_leaves, on=["emp_id", "date"], how="left"
    )
else:
    df_master["is_leave"] = False

df_master["is_leave"] = df_master["is_leave"].fillna(False)

# 5. Holidays Mapping
df_holidays["is_holiday"] = True
df_master = pd.merge(
    df_master,
    df_holidays[["holiday_date", "scope", "is_holiday"]],
    left_on=["date", "plant"],
    right_on=["holiday_date", "scope"],
    how="left",
)
df_master["is_holiday"] = df_master["is_holiday"].fillna(False)


# 6. Attendance Status Priority Order (Rule 12)
def assign_status(row):
    if row["date"].dayofweek == 6 and row["punch_count"] == 0:
        return "Weekly Off"
    if row["is_holiday"] and row["punch_count"] == 0:
        return "Holiday"
    if row["is_leave"]:
        return "On Leave"
    if row["punch_count"] >= 2:
        return "Present"
    if row["punch_count"] == 1:
        return "Missing Punch"
    return "Absent"


print("Calculating attendance status for all employees...")
df_master["attendance_status"] = df_master.apply(assign_status, axis=1)

df_master.to_csv("daily_attendance_master.csv", index=False)
print(
    "Part 3 complete! Daily attendance master saved to 'daily_attendance_master.csv'."
)