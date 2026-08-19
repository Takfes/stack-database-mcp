CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

INSERT INTO products (name, price) VALUES
    ('Widget', 9.99),
    ('Gadget', 24.50),
    ('Gizmo', 5.00);

CREATE TABLE inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT INTO inventory (product_id, quantity) VALUES
    (1, 100),
    (2, 40),
    (3, 250);

-- Read-only user: matches the Postgres mcp_readonly role for parity.
CREATE USER 'mcp_readonly'@'%' IDENTIFIED BY 'readonly';
GRANT SELECT ON appdb.* TO 'mcp_readonly'@'%';
FLUSH PRIVILEGES;
