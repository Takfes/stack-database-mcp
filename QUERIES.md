# QUERIES.md

**Copy-Paste Test Script (Execution Order)**
Use each line as a standalone prompt.

1. List all **PostgreSQL** schemas using `dbtools` only.
2. List all **PostgreSQL** schemas using `pgquery` only.
3. List all **PostgreSQL** tables using `dbtools` only.
4. List all **PostgreSQL** tables using `pgquery` only.
5. Show the row count of **PostgreSQL** `orders` using `dbtools` only.
6. Show the row count of **PostgreSQL** `orders` using `pgquery` only.
7. Show detailed metadata (columns, constraints, indexes) for **PostgreSQL** `orders` using `dbtools` only.
8. Run a full health check (all categories) on **PostgreSQL** using `pgquery` only.
9. List all **MySQL** tables using `dbtools` only.
10. List all **MySQL** tables using the dedicated **MySQL MCP** server only.
11. Show the row count of **MySQL** `products` using `dbtools` only.
12. Show the row count of **MySQL** `products` using the dedicated **MySQL MCP** server only.
13. Show detailed metadata for **MySQL** `products` and `inventory` using `dbtools` only.
14. Join **MySQL** `products` and `inventory` and compute stock value per item using the dedicated **MySQL MCP** server only.
15. List all **MSSQL** tables using `dbtools` only.
16. List all **MSSQL** tables using the dedicated **MSSQL MCP** server only.
17. Show the row count of **MSSQL** `employees` using `dbtools` only.
18. Show the row count of **MSSQL** `employees` using the dedicated **MSSQL MCP** server only.
19. Calculate the cumulative length of **MSSQL** `departments.name` using `dbtools` only.
20. Join **MSSQL** `employees` to `departments` on `employee_id` using the dedicated **MSSQL MCP** server only.
