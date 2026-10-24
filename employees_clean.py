import pandas as pd

# 1. Files Load Karein
print("Loading files...")
df_emp = pd.read_csv("employees.csv")
df_dept = pd.read_csv("departments.csv")

# 2. Employees Deduplication (Rule 1)
# updated_at ko datetime me convert karein taaki sahi se sort ho sake
df_emp["updated_at"] = pd.to_datetime(df_emp["updated_at"])

# emp_id ke mutabiq sort karein aur latest updated_at ko upar rakhein
df_emp = df_emp.sort_values(by=["emp_id", "updated_at"], ascending=[True, False])

# Har emp_id ki sirf pehli row (latest wali) rakhain, baaki drop kardein
df_emp_clean = df_emp.drop_duplicates(subset=["emp_id"], keep="first").copy()
print(
    f"Total unique employees after deduplication: {len(df_emp_clean)}"
)  # noqa: E501

# 3. Department Names Cleaning & Old Names Mapping
# Extra spaces khatam karna aur text formatting theek karna (Title case)
df_emp_clean["department"] = (
    df_emp_clean["department"].astype(str).str.strip().str.title()
)
df_dept["dept_name"] = df_dept["dept_name"].astype(str).str.strip().str.title()
df_dept["previous_name"] = (
    df_dept["previous_name"].astype(str).str.strip().str.title()
)

# departments.csv se purane naam (previous_name) aur naye naam ki mapping banana
# (Agar kisi record me purana naam hai, toh use naye dept_name se replace kar dein)
prev_to_new_map = dict(
    zip(df_dept["previous_name"].dropna(), df_dept["dept_name"])
)

# Department names ko map kar ke update karna
df_emp_clean["department"] = df_emp_clean["department"].replace(
    prev_to_new_map
)

# Cleaned data ko save kar lein taaki aage ke parts me use ho sake
df_emp_clean.to_csv("employees_cleaned.csv", index=False)
print("Part 1 complete! Cleaned data saved to 'employees_cleaned.csv'.")