import sqlite3
import pandas as pd

conn=sqlite3.connect('cec.db')
conn.execute('PRAGMA foreign_keys=ON')

pd.read_csv("data/departments.csv").to_sql(
    "departments",
    conn,
    if_exists="replace",
    index=False
)

pd.read_csv("data/grants_clean.csv").to_sql(
    "grants",
    conn,
    if_exists="replace",
    index=False
)

conn.close()
