CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);

INSERT INTO customers (name, email) VALUES
    ('Ada Lovelace', 'ada@example.com'),
    ('Alan Turing', 'alan@example.com'),
    ('Grace Hopper', 'grace@example.com');

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    amount NUMERIC(10, 2) NOT NULL
);

INSERT INTO orders (customer_id, amount) VALUES
    (1, 42.50),
    (2, 17.00),
    (3, 99.99);

-- Read-only role: proves enforcement at the database grant, not just an MCP flag.
CREATE ROLE mcp_readonly LOGIN PASSWORD 'readonly';
GRANT CONNECT ON DATABASE appdb TO mcp_readonly;
GRANT USAGE ON SCHEMA public TO mcp_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_readonly;
