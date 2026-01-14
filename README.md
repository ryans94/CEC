# CEC data workspace

This directory is a small SQLite-based data workspace.

## What is here
- `cec.db`: SQLite database generated from the schema and CSVs.
- `schema.sql`: SQL schema that defines `departments` and `grants` tables.
- `import.py`: Loads CSVs in `data/` into `cec.db` using pandas.
- `rebuild.sh`: Convenience script to delete and rebuild the database, then import data.
- `data/`: Source CSVs (`departments.csv`, `grants_clean.csv`, `grants_raws.csv`).

## Typical workflow
1. Update CSVs in `data/` as needed.
2. Rebuild the database and import data:

```bash
bash rebuild.sh
```

## Notes
- The database uses foreign keys; `department_id` in `grants` must exist in `departments`.
- `import.py` replaces the `departments` and `grants` tables on each run.
