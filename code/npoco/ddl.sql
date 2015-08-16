
-- Schema:
CREATE SCHEMA sample;

-- Tables:
CREATE TABLE sample.address (
	address_id SERIAL PRIMARY KEY,
	street TEXT NOT NULL,
	house_no TEXT NOT NULL,
	city TEXT NOT NULL	
);

CREATE TABLE sample.person (
	person_id SERIAL PRIMARY KEY,
	firstname TEXT NOT NULL,
	lastname TEXT NOT NULL,
	age INTEGER NOT NULL,
	address_id INTEGER REFERENCES sample.address (address_id)
);

