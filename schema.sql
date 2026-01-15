PRAGMA foreign_keys=ON;

DROP TABLE IF EXISTS grants;
DROP TABLE IF EXISTS capabilities;
DROP TABLE IF EXISTS departments;


CREATE TABLE departments(
	department_id TEXT PRIMARY KEY,
	department_name TEXT UNIQUE NOT NULL
);

CREATE TABLE capabilities(
	capabilities_id TEXT PRIMARY KEY,
	capability_name TEXT
);

CREATE TABLE capability_departments(
	capabilities_id TEXT NOT NULL,
	department_id TEXT NOT NULL,
	PRIMARY KEY (capabilities_id, department_id),
	FOREIGN KEY (capabilities_id) REFERENCES capabilities(capabilities_id),
	FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE grants(
	grant_id TEXT PRIMARY KEY,
	funding TEXT,
	sponsor TEXT,
	awardee TEXT,
	title TEXT,
	date TEXT,
	capabilities_id TEXT,
	department_id TEXT NOT NULL,
	FOREIGN KEY (capabilities_id) REFERENCES capabilities(capabilities_id),
	FOREIGN KEY (department_id) REFERENCES departments(department_id)
);
