DROP DATABASE IF EXISTS hello;
DROP USER IF EXISTS hello;

CREATE USER hello WITH PASSWORD 'ravello';
CREATE DATABASE hello OWNER hello;

\connect hello

DROP TABLE IF EXISTS visits;
CREATE TABLE visits (
    id SERIAL,
    datetime TIMESTAMP,
    address INET,
    request VARCHAR(255),
    user_agent VARCHAR(255)
);
ALTER TABLE visits OWNER TO hello;
