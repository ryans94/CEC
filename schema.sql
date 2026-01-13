PRAGMA foreign_keys=ON;

CREATE TABLE departments(
	department_id TEXT PRIMARY KEY,
	department_name TEXT UNIQUE NOT NULL
);

CREATE TABLE grants(
	grant_id TEXT PRIMARY KEY,
	funding TEXT,
	sponsor TEXT,
	awardee TEXT,
	title TEXT,
	date TEXT,
	department_id TEXT NOT NULL,
	FOREIGN KEY (department_id) REFERENCES departments(department_id)
);