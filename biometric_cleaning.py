import pandas as pd

# 1. Biometric punches aur device mapping files load karein
print("Loading biometric and mapping files...")
df_punches = pd.read_csv("biometric_punches.csv")
df_mapping = pd.read_csv("device_mapping.csv")

# punch_time ko datetime format me convert karein
df_punches["punch_time"] = pd.to_datetime(df_punches["punch_time"])

# 2. Device Mapping (Rule 8)
# device_id aur device_user_id par merge karein
df_merged = pd.merge(
    df_punches,
    df_mapping,
    on=["device_id", "device_user_id"],
    how="left",
    indicator=True,
)

# Jo map nahi hue (contractors / visitors), unhe rejected table me daal dein
df_rejected = df_merged[df_merged["_merge"] == "left_only"].copy()
df_rejected = df_rejected.drop(columns=["_merge"])
df_rejected.to_csv("rejected_punches.csv", index=False)
print(
    f"Unmapped / Rejected punches saved: {len(df_rejected)} rows -> 'rejected_punches.csv'"
)  # noqa: E501

# Sirf valid (mapped) punches ko aage ke liye rakhein
df_valid = df_merged[df_merged["_merge"] == "both"].copy()
df_valid = df_valid.drop(columns=["_merge"])

# 3. 2-Minute Duplicate Removal Rule (Rule 9)
# Employees aur punch_time ke mutabiq sort karein
df_valid = df_valid.sort_values(by=["emp_id", "punch_time"])

# Har employee ke pichle punch se time difference nikalein
df_valid["time_diff"] = df_valid.groupby("emp_id")["punch_time"].diff()

# Agar time difference 2 minute ya us se kam hai, toh wo duplicate hai (use drop kar dein)
two_mins = pd.Timedelta(minutes=2)
df_clean_punches = df_valid[
    df_valid["time_diff"].isna() | (df_valid["time_diff"] > two_mins)
].copy()

# Faltu column drop kar dein
df_clean_punches = df_clean_punches.drop(columns=["time_diff"])

# Cleaned punches ko save kar lein
df_clean_punches.to_csv("biometric_punches_cleaned.csv", index=False)
print(
    f"Part 2 complete! Cleaned punches: {len(df_clean_punches)} rows -> 'biometric_punches_cleaned.csv'"
)