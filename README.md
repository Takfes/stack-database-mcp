# stack-database-mcp

Disposable Postgres + MySQL + MSSQL stack for testing MCP database servers before they ship
in `indie-marketplace`'s `database` plugin. POC only — throwaway passwords, reseeded every run.

## Quick start

```bash
docker compose up -d
docker ps -a --format '{{.Names}}: {{.Status}}'   # wait for all three "(healthy)"
```

`mysql-mcp`/`mssql-mcp` have no published image — build once locally:

```bash
docker build -t stack-database-mcp-mysql-mcp:local https://github.com/benborla/mcp-server-mysql.git
```

```bash
git clone --depth 1 https://github.com/JexinSam/mssql_mcp_server.git /tmp/mssql_mcp_server
sed -i '' '/COPY pyproject.toml \./a\
COPY README.md .
' /tmp/mssql_mcp_server/Dockerfile
docker build -t stack-database-mcp-mssql-mcp:local /tmp/mssql_mcp_server
```

- MSSQL boots slowest of the three. `dbtools` connects to all 3 DBs at startup with **no
  retry** — if it fails, wait until all containers show `healthy`, then reconnect the MCP
  server.
- JexinSam's upstream Dockerfile is missing `COPY README.md .` (its build backend needs it) —
  patched above.

Open in **Claude Code** or **VS Code** — 4 servers pre-wired, nothing else to configure:

| Server | Engine(s) | Covers |
|---|---|---|
| `pgquery` | Postgres | dedicated, second independent SQL validator |
| `dbtools` | Postgres, MySQL, MSSQL | one generic server, all 3 engines |
| `mysql-mcp` | MySQL | dedicated, app-level write gate |
| `mssql-mcp` | MSSQL | dedicated, regex-gated read tool |

Ask the agent directly — all return seeded rows (Ada Lovelace, Widget, Katherine Johnson):

- `pgquery`: "Using the pgquery MCP tool, SELECT * FROM customers."
- `dbtools`: "Using the dbtools MCP tool, list the products from the MySQL database."
- `mysql-mcp`: "Using the mysql-mcp MCP tool, list the products in the database."
- `mssql-mcp`: "Using the mssql-mcp MCP tool, list the employees in the database."

More prompts (introspection, joins, cross-server): [`QUERIES.md`](./QUERIES.md).

```bash
docker compose down   # tear down
```

## Manual verification — bypassing MCP

Seed data:

```bash
docker exec stack-database-mcp-postgres-1 psql -U admin -d appdb -c "SELECT * FROM customers;"
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb -c "SELECT * FROM orders;"
docker exec stack-database-mcp-mysql-1 mysql -uroot -padmin appdb -e "SELECT * FROM products; SELECT * FROM inventory;"
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Admin123!" -C -d appdb -Q "SELECT * FROM employees;"
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U mcp_readonly -P "Readonly123!" -C -d appdb -Q "SELECT * FROM departments;"
```

Read-only enforcement — all should fail (DB grant, not just the MCP server's own flag):

```bash
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb -c "INSERT INTO customers (name, email) VALUES ('Hacker', 'x@x.com');"
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb -c "DELETE FROM customers WHERE id = 1;"
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U mcp_readonly -P "Readonly123!" -C -d appdb -Q "INSERT INTO employees (name, title) VALUES ('Hacker', 'x');"
```

## Manual verification — through MCP

All servers connect as `mcp_readonly`. Verified via direct protocol test + `scripts/smoke_test.py` Tier 2b.

- **`pgquery`** (`crystaldba/postgres-mcp`, `--access-mode=restricted`) — SELECT works;
  INSERT/DELETE rejected by its own validator, a second layer on top of the DB grant. Quirk:
  rejections come back as `isError: false` with the error text embedded in the content — check
  the text, not just `isError`. Docker-only; `uvx postgres-mcp` is broken upstream
  (`NEXTME.md`).
- **`dbtools`** (`googleapis/genai-toolbox`, `tools.yaml`) — fixed tools
  (`query-customers`/`query-products`/`query-employees`) work; `insert-customer`/
  `delete-product` rejected (`isError: true`). Ad-hoc (`*-execute-sql`) and introspection
  (`*-list-tables`, `postgres-list-schemas`) confirmed per engine — no `mssql-list-schemas`
  equivalent exists upstream. No independent validator of its own; enforcement is the DB grant
  only.
- **`mysql-mcp`** (`benborla/mcp-server-mysql`, `mysql_query`) — SELECT works; INSERT rejected
  via `ALLOW_*_OPERATION` env flags (set `false` in `.env` — the image's own Dockerfile
  defaults them `true`, so this override is load-bearing).
- **`mssql-mcp`** (`JexinSam/mssql_mcp_server`, `query_sql`/`execute_sql`) — SELECT works;
  `query_sql` regex-gates to `SELECT`/`WITH`/`SHOW` (verified in source). `execute_sql` stays
  unrestricted by upstream design.

## Dual-client verification

- **Claude Code** reads `.mcp.json` directly — verified via `claude -p`
  (`--allowedTools mcp__<server>`), automated in Tier 3. One-shot sessions leave containers
  running after exit (`docker rm -f` as needed).
- **VS Code** — Agent Host reads root `.mcp.json` directly; classic Copilot Chat Agent Mode
  reads `.vscode/mcp.json` (root key `servers`), added as a backward-compatible net.
- Both manually confirmed working end-to-end.

## Smoke test

```bash
docker compose up -d
python3 scripts/smoke_test.py
```

3 tiers, 25 checks, all `[PASS]`:

- **Tier 1** — Docker healthcheck per DB, no MCP.
- **Tier 2** — raw SQL per engine (no MCP) + every MCP tool call above.
- **Tier 3** — live `claude -p` NL question per server, asserts on the final answer. Needs
  `claude` installed/authenticated; `SMOKE_TEST_SKIP_AGENT=1` to skip.

## Credentials

`.env` is the single source of truth:

- Docker-based `.mcp.json` entries pass `--env-file .env` to `docker run`.
- `pgquery` reads `DATABASE_URI`; `mysql-mcp`/`mssql-mcp` read their own upstream var names.
- `dbtools` reads `tools.yaml`, `${VAR}` placeholders resolved natively by `genai-toolbox`.
- `tools.yaml` is tracked as-is, no `.example` step.
- All values throwaway, reseeded every `docker compose up`.

## Tear down

```bash
docker compose down
```
