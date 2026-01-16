import sqlite3
import pandas as pd

def clean_csv(path):
    df = pd.read_csv(path)
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    return df

conn = sqlite3.connect("data/db/cec.db")
conn.execute("PRAGMA foreign_keys = ON")

clean_csv("data/csv/departments.csv").to_sql(
    "departments", conn, if_exists="append", index=False
)

capabilities_df = clean_csv("data/csv/capabilities.csv")
capabilities_df[["capabilities_id", "capability_name"]].to_sql(
    "capabilities", conn, if_exists="append", index=False
)

cap_dept_rows = []
for _, row in capabilities_df.iterrows():
    cap_id = str(row["capabilities_id"]).strip()
    departments = str(row["department_id"]).split(",")
    for dept_id in departments:
        dept_id = dept_id.strip()
        if dept_id:
            cap_dept_rows.append(
                {"capabilities_id": cap_id, "department_id": dept_id}
            )

pd.DataFrame(cap_dept_rows).to_sql(
    "capability_departments", conn, if_exists="append", index=False
)

clean_csv("data/csv/grants_clean.csv").to_sql(
    "grants", conn, if_exists="append", index=False
)

conn.close()
