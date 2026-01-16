# CEC data workspace

This directory is a small SQLite-based data workspace.

## What is here
- `data/db/cec.db`: SQLite database generated from the schema and CSVs.
- `schema.sql`: SQL schema that defines `departments` and `grants` tables.
- `import.py`: Loads CSVs in `data/csv/` into `data/db/cec.db` using pandas.
- `rebuild.sh`: Convenience script to delete and rebuild the database, then import data.
- `scrapers/scrape_faculty.py`: Web scraper for faculty data from GMU catalog.
- `scrapers/scrape_grants.py`: Web scraper for grants data from CEC grants page.
- `scrapers/grants_page.html`: Saved HTML page for offline scraping (not in git).
- `data/`: Data directory containing CSVs and database.

## Initial Setup
```bash
# Create and activate virtual environment
python3 -m venv venv

source venv/bin/activate  
# OR if on Windows: 
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Build the database
python import.py
```

## Typical workflow
1. Update CSVs in `data/` as needed.
2. Rebuild the database and import data:

```bash
bash rebuild.sh
```

## Scraping Faculty Data

```bash
# Scrape faculty from College of Engineering and Computing
python3 scrape_faculty.py

# For other colleges:
# 1. Edit scrape_faculty.py and update TARGET_URL
# 2. Ensure all departments are in data/departments.csv
# 3. Run: python3 scrape_faculty.py
```

## Directory Structure
```
.
├── data/                     # Data directory
│   ├── csv/                  # CSV files
│   │   ├── departments.csv       # Department definitions
│   │   ├── capabilities.csv      # Capability definitions
│   │   ├── grants_clean.csv      # Cleaned grant data
│   │   ├── grants_raws.csv       # Raw grant data
│   │   ├── grants_cec.csv        # Scraped CEC grants
│   │   └── faculty.csv           # Faculty data
│   └── db/                   # Database files
│       └── cec.db                # SQLite database
├── scrapers/                 # Web scraping scripts
│   ├── scrape_faculty.py         # Faculty web scraper
│   ├── scrape_grants.py          # Grants web scraper
│   └── grants_page.html          # Saved grants page (not in git)
├── schema.sql                # Database schema definition
├── import.py                 # Imports CSV data into database
├── rebuild.sh                # Rebuilds database from scratch
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Dependencies

- Python 3.7+
- pandas
- requests
- beautifulsoup4

## Notes
- The database uses foreign keys; `department_id` in `grants` must exist in `departments`.
- `import.py` replaces the `departments` and `grants` tables on each run.
- Faculty scraper automatically continues numbering from existing faculty.csv
- Department matching in scraper is case-insensitive and supports partial matches