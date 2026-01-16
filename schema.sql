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

CREATE TABLE faculty(
	faculty_id TEXT PRIMARY KEY,
	full_name TEXT,
	first_name TEXT,
	last_name TEXT,
	first_last TEXT,
	title TEXT,
	department_id TEXT,
	college TEXT,
	academic_history TEXT,
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
	faculty_id TEXT,
	FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id),
	FOREIGN KEY (capabilities_id) REFERENCES capabilities(capabilities_id),
	FOREIGN KEY (department_id) REFERENCES departments(department_id)
);
