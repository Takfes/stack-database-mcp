# stack-database-mcp

Disposable Postgres + MySQL stack for testing the `pgquery`/`dbtools` MCP servers before they ship in `indie-marketplace`'s `database` plugin. Not for production use — passwords are throwaway defaults, seeded fresh every time.

## Spin up

```bash
docker compose up -d
docker ps -a --format '{{.Names}}: {{.Status}}'   # wait until both show (healthy)
```

## Manually verify seed data

```bash
# Postgres, as admin
docker exec stack-database-mcp-postgres-1 psql -U admin -d appdb -c "SELECT * FROM customers;"

# Postgres, as the read-only role
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb -c "SELECT * FROM orders;"

# MySQL
docker exec stack-database-mcp-mysql-1 mysql -uroot -padmin appdb -e "SELECT * FROM products; SELECT * FROM inventory;"
```

## Manually verify read-only enforcement

Both should fail with `permission denied` — proving read-only is enforced at the database grant, not just trusted to an MCP server's own flag:

```bash
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb \
  -c "INSERT INTO customers (name, email) VALUES ('Hacker', 'x@x.com');"

docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb \
  -c "DELETE FROM customers WHERE id = 1;"
```

## Manually verify through the actual MCP server (not just the raw database)

`.mcp.json` wires up `pgquery` (`crystaldba/postgres-mcp`, Docker, `--access-mode=restricted`) connected as `mcp_readonly` — open this project in Claude Code and it's live. Confirmed working end-to-end via a direct protocol test (init → `tools/list` → `tools/call execute_sql`):

- `SELECT * FROM customers;` → returns the seeded rows.
- `INSERT ...` / `DELETE ...` → both rejected with `Error validating query: ...` — note this is a **second, independent layer**: postgres-mcp's own restricted-mode SQL validator refuses the write before it ever reaches Postgres, on top of (not instead of) the `mcp_readonly` role's grant-level enforcement proven above.
- One quirk worth knowing: postgres-mcp reports these validation failures as a normal successful tool result (`isError: false`) with the error text embedded in the content — a caller that only checks the `isError` flag will miss the failure, it has to read the text.

`uvx postgres-mcp` currently fails locally with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` (a real dependency-resolution issue in the package, not a local cache problem — confirmed via `uvx --refresh`). Use the Docker command above until that's fixed upstream. There's no `npm`/`npx` install path either — it's a Python-only package, so Docker is currently the *only* working way to run it. Tracked as a risk for the eventual `database` plugin in `NEXTME.md`.

`.mcp.json` also wires up `dbtools` (`googleapis/genai-toolbox`, Docker, driven by `tools.yaml`) with four fixed tools: `query-customers`/`query-products` (read) and `insert-customer`/`delete-product` (expected to fail). Requires `tools.yaml` to exist locally first — see Credentials below. Confirmed working end-to-end via the same direct protocol test:

- `query-customers` / `query-products` → return the seeded rows from Postgres and MySQL respectively, proving one server can front both engines off a single `tools.yaml`.
- `insert-customer` / `delete-product` → both rejected with `isError: true` and the underlying DB error surfaced verbatim (`permission denied for table customers` / `DELETE command denied to user 'mcp_readonly'`). Unlike postgres-mcp, dbtools sets `isError` correctly — no quirk to work around here.
- dbtools has no independent query-validation layer of its own (unlike postgres-mcp's restricted-mode validator) — enforcement here is entirely the `mcp_readonly` grant on each database. That's expected: dbtools' access model is "whatever SQL the tool author hardcoded, against whatever DB user is configured," not a general-purpose SQL gate.
- `tools.yaml.example` also declares ad-hoc + schema-introspection tools for Postgres and MySQL: `postgres-execute-sql`/`mysql-execute-sql` (run arbitrary SQL, not just the four hardcoded statements above) and `postgres-list-tables`/`postgres-list-schemas`/`mysql-list-tables` (inspect schema without hand-writing SQL). This is a deliberate tradeoff, not an oversight: ad-hoc execute-sql tools are less safe than the fixed statements — they let a caller run any statement the `mcp_readonly` grant permits, rather than only the exact query the tool author wrote — so the same grant-level enforcement (read-only role) is the only thing standing between an ad-hoc call and a destructive one. Use the fixed-statement tools where the query is known ahead of time; reach for the ad-hoc tools only when the caller genuinely needs open-ended SQL.

## Dual-client verification

**Claude Code** — confirmed working through a real `claude` CLI session (not just the protocol probes above), pointed at this project's own `.mcp.json`:

```bash
docker compose up -d
claude -p "Using the pgquery MCP tool, SELECT * FROM customers, then try an INSERT and report what happened."
```

Returned the three seeded customers, then a rejected INSERT (`Error validating query: ...`). Same session, `dbtools`' `query-products`/`query-customers` tools also confirmed working, returning correct rows from both MySQL and Postgres through one server. One thing worth knowing: `claude -p` (one-shot mode) left the MCP servers' Docker containers running after the CLI process exited each time, rather than cleaning them up — not a correctness problem, but if you drive this project the same way, `docker ps` and `docker rm -f` afterward.

**VS Code** — not verified. Driving VS Code's MCP integration needs either a human at the keyboard or VS Code-specific automation this environment doesn't have; the `vscode-mcp.json` files this marketplace generates haven't been exercised against a live VS Code session yet. If you want this closed out, run VS Code by hand against this stack's generated `vscode-mcp.json` and confirm the same query works.

## Smoke test

`scripts/smoke_test.py` automates the manual MCP-protocol checks above — SELECT/INSERT through `pgquery`, and one `dbtools` query against each database. Requires the stack to be up and `tools.yaml` to exist locally (see Credentials below):

```bash
docker compose up -d
python3 scripts/smoke_test.py
```

### MSSQL

The MSSQL container is Microsoft's Express-edition SQL Server image. `ACCEPT_EULA=Y` in `docker-compose.yml` is a real, unavoidable requirement of this image — it will refuse to start without it, not an optional toggle.

```bash
# as sa
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Admin123!" -C -d appdb -Q "SELECT * FROM employees;"

# as the read-only login
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U mcp_readonly -P "Readonly123!" -C -d appdb -Q "SELECT * FROM departments;"
```

Read-only enforcement, proven the same way as Postgres/MySQL — this should fail:

```bash
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U mcp_readonly -P "Readonly123!" -C -d appdb \
  -Q "INSERT INTO employees (name, title) VALUES ('Hacker', 'x');"
```

## Credentials

Copy `.env.example` → `.env` and `tools.yaml.example` → `tools.yaml` if pointing a real MCP server at this stack. Both already match what's seeded here — no values to invent. `dbtools` in `.mcp.json` depends on `tools.yaml` existing locally (it's bind-mounted by absolute path); copy it before opening this project in Claude Code.

## Tear down

```bash
docker compose down
```
