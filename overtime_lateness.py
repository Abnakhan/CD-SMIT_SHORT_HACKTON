import json
import pandas as pd

print("1. Loading daily attendance master and shift details...")
df_master = pd.read_csv("daily_attendance_master.csv")

with open("shifts.json", "r") as f:
    shifts_data = json.load(f)

# Shift mapping dictionary
shift_dict = {
    "DAY": {"start": "08:00:00", "end": "16:00:00", "crosses_midnight": False},
    "EVE": {"start": "16:00:00", "end": "00:00:00", "crosses_midnight": False},
    "NIGHT": {"start": "00:00:00", "end": "08:00:00", "crosses_midnight": False},
    "GEN": {"start": "09:00:00", "end": "17:00:00", "crosses_midnight": False},
}

if isinstance(shifts_data, dict):
    for code, details in shifts_data.items():
        if isinstance(details, dict):
            shift_dict[code] = {
                "start": details.get("start_time", "09:00:00"),
                "end": details.get("end_time", "17:00:00"),
                "crosses_midnight": details.get("crosses_midnight", False),
            }
elif isinstance(shifts_data, list):
    for item in shifts_data:
        if isinstance(item, dict):
            code = (
                item.get("shift_code")
                or item.get("code")
                or item.get("shift")
                or item.get("id")
            )
            if code:
                shift_dict[code] = {
                    "start": item.get("start_time", "09:00:00"),
                    "end": item.get("end_time", "17:00:00"),
                    "crosses_midnight": item.get("crosses_midnight", False),
                }

print("2. Mapping shift timings...")
df_master["start_time"] = df_master["shift_code"].map(
    lambda x: shift_dict.get(x, shift_dict["GEN"])["start"]
)
df_master["end_time"] = df_master["shift_code"].map(
    lambda x: shift_dict.get(x, shift_dict["GEN"])["end"]
)
df_master["crosses_midnight"] = df_master["shift_code"].map(
    lambda x: shift_dict.get(x, shift_dict["GEN"])["crosses_midnight"]
)

# Datetime conversion
print("3. Converting datetimes...")
dates_dt = pd.to_datetime(df_master["date"], format="mixed", errors="coerce")
df_master["date_str"] = dates_dt.dt.strftime("%Y-%m-%d")
df_master["day_of_week"] = dates_dt.dt.day_of_week

df_master["check_in"] = pd.to_datetime(
    df_master["check_in"], format="mixed", errors="coerce"
)
df_master["check_out"] = pd.to_datetime(
    df_master["check_out"], format="mixed", errors="coerce"
)

# Vectorized shift datetimes
df_master["shift_start_dt"] = pd.to_datetime(
    df_master["date_str"] + " " + df_master["start_time"], errors="coerce"
)
df_master["shift_end_dt"] = pd.to_datetime(
    df_master["date_str"] + " " + df_master["end_time"], errors="coerce"
)
midnight_mask = df_master["crosses_midnight"] == True
df_master.loc[midnight_mask, "shift_end_dt"] += pd.Timedelta(days=1)

print("4. Calculating late arrivals and early departures...")
is_working_day = (
    (df_master["day_of_week"] != 6)
    & (~df_master["is_holiday"])
    & (df_master["attendance_status"] == "Present")
)

df_master["is_late"] = False
df_master["is_early_departure"] = False

late_cond = is_working_day & (
    df_master["check_in"]
    > (df_master["shift_start_dt"] + pd.Timedelta(minutes=10))
)
df_master.loc[late_cond, "is_late"] = True

early_cond = is_working_day & (
    df_master["check_out"]
    < (df_master["shift_end_dt"] - pd.Timedelta(minutes=10))
)
df_master.loc[early_cond, "is_early_departure"] = True

print("5. Calculating overtime hours (Vectorized)...")
df_master["calculated_ot_hours"] = 0.0

present_mask = df_master["attendance_status"] == "Present"
sunday_or_holiday = present_mask & (
    (df_master["day_of_week"] == 6) | (df_master["is_holiday"])
)
normal_day = present_mask & ~((df_master["day_of_week"] == 6) | (df_master["is_holiday"]))

# Sunday / Holiday OT
sun_mins = (
    df_master.loc[sunday_or_holiday, "check_out"]
    - df_master.loc[sunday_or_holiday, "check_in"]
).dt.total_seconds() / 60
sun_ot = (sun_mins.clip(lower=0) // 30) * 0.5
df_master.loc[sunday_or_holiday, "calculated_ot_hours"] = sun_ot.fillna(0.0)

# Normal Working Day OT
norm_mins = (
    df_master.loc[normal_day, "check_out"]
    - df_master.loc[normal_day, "shift_end_dt"]
).dt.total_seconds() / 60
norm_ot = ((norm_mins - 30) // 30).clip(lower=0) * 0.5
df_master.loc[normal_day, "calculated_ot_hours"] = norm_ot.fillna(0.0)

# Result save karein
output_cols = [
    "emp_id",
    "date",
    "plant",
    "department",
    "shift_code",
    "attendance_status",
    "check_in",
    "check_out",
    "is_late",
    "is_early_departure",
    "calculated_ot_hours",
]
print("6. Saving final output to 'daily_attendance_with_ot.csv'...")
df_master[output_cols].to_csv("daily_attendance_with_ot.csv", index=False)
print(
    "Part 4 complete successfully in seconds! You can now run python monthly_summary.py."
)