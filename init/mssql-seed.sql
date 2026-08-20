CREATE TABLE employees (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    title NVARCHAR(255) NOT NULL
);

INSERT INTO employees (name, title) VALUES
    ('Katherine Johnson', 'Mathematician'),
    ('Margaret Hamilton', 'Software Engineer'),
    ('Dorothy Vaughan', 'Programmer');

CREATE TABLE departments (
    id INT IDENTITY(1,1) PRIMARY KEY,
    employee_id INT NOT NULL REFERENCES employees(id),
    name NVARCHAR(255) NOT NULL
);

INSERT INTO departments (employee_id, name) VALUES
    (1, 'Flight Dynamics'),
    (2, 'Software Engineering'),
    (3, 'Programming');

-- Read-only login: matches the Postgres mcp_readonly role / MySQL mcp_readonly user for parity.
CREATE LOGIN mcp_readonly WITH PASSWORD = 'Readonly123!';
CREATE USER mcp_readonly FOR LOGIN mcp_readonly;
GRANT SELECT ON employees TO mcp_readonly;
GRANT SELECT ON departments TO mcp_readonly;
