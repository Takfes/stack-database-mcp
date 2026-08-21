# stack-database-mcp

Disposable Postgres + MySQL + MSSQL stack for testing MCP database servers before they ship in `indie-marketplace`'s `database` plugin. Not for production use — passwords are throwaway defaults, seeded fresh every time.

## TL;DR — verify all three databases are reachable through the MCP agent

```bash
docker compose up -d
docker ps -a --format '{{.Names}}: {{.Status}}'   # wait until all three show (healthy)
```

Open this project in **Claude Code** or **VS Code** — five MCP servers are pre-wired, nothing else to configure:

| Server | Engine(s) | Covers |
|---|---|---|
| `pgquery` | Postgres | dedicated, second independent SQL-validator layer |
| `dbtools` | Postgres, MySQL, MSSQL | one generic server, all three engines |
| `mysql-mcp` | MySQL | dedicated, app-level write gate |
| `mssql-mcp` | MSSQL | dedicated, regex-gated read-only tool |

Ask the agent to run each of these through its MCP tools — all should return seeded rows (Ada Lovelace, Widget, Katherine Johnson):

- `pgquery` → `SELECT * FROM customers;`
- `dbtools` → `query-products` (MySQL) or `query-employees` (MSSQL)
- `mysql-mcp` → `mysql_query` with `SELECT * FROM products;`
- `mssql-mcp` → `query_sql` with `SELECT * FROM employees;`

Then tear down:

```bash
docker compose down
```

The sections below cover the same ground in more depth, plus read-only-enforcement and rejection-path checks.

## Spin up

```bash
docker compose up -d
docker ps -a --format '{{.Names}}: {{.Status}}'   # wait until all three show (healthy)
```

`mysql-mcp` and `mssql-mcp` (the dedicated per-flavor MCP servers in `.mcp.json`) have no published image — build them locally once, from each upstream's own Dockerfile:

```bash
docker build -t stack-database-mcp-mysql-mcp:local https://github.com/benborla/mcp-server-mysql.git
```

`mssql_mcp_server`'s upstream Dockerfile has a bug — it never copies `README.md` into the build context, but `pyproject.toml`'s build backend requires it, so the image fails to build as-is. Build from a locally patched copy (adds one `COPY README.md .` line):

```bash
git clone --depth 1 https://github.com/JexinSam/mssql_mcp_server.git /tmp/mssql_mcp_server
sed -i '' '/COPY pyproject.toml \./a\
COPY README.md .
' /tmp/mssql_mcp_server/Dockerfile
docker build -t stack-database-mcp-mssql-mcp:local /tmp/mssql_mcp_server
```

## Manually verify seed data

```bash
# Postgres, as admin
docker exec stack-database-mcp-postgres-1 psql -U admin -d appdb -c "SELECT * FROM customers;"

# Postgres, as the read-only role
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb -c "SELECT * FROM orders;"

# MySQL
docker exec stack-database-mcp-mysql-1 mysql -uroot -padmin appdb -e "SELECT * FROM products; SELECT * FROM inventory;"

# MSSQL — ACCEPT_EULA=Y in docker-compose.yml is a real, unavoidable requirement of
# Microsoft's Express-edition image, not an optional toggle.
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "Admin123!" -C -d appdb -Q "SELECT * FROM employees;"
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U mcp_readonly -P "Readonly123!" -C -d appdb -Q "SELECT * FROM departments;"
```

## Manually verify read-only enforcement

These should all fail — proving read-only is enforced at the database grant, not just trusted to an MCP server's own flag:

```bash
# Postgres
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb \
  -c "INSERT INTO customers (name, email) VALUES ('Hacker', 'x@x.com');"
docker exec stack-database-mcp-postgres-1 psql -U mcp_readonly -d appdb \
  -c "DELETE FROM customers WHERE id = 1;"

# MSSQL
docker exec stack-database-mcp-mssql-1 /opt/mssql-tools18/bin/sqlcmd -S localhost -U mcp_readonly -P "Readonly123!" -C -d appdb \
  -Q "INSERT INTO employees (name, title) VALUES ('Hacker', 'x');"
```

## Manually verify through the actual MCP server (not just the raw database)

Every server below connects as `mcp_readonly`. Confirmed working end-to-end via a direct protocol test (init → `tools/list` → `tools/call`), and covered by `scripts/smoke_test.py`'s Tier 2b.

**`pgquery`** (`crystaldba/postgres-mcp`, dedicated Postgres, `--access-mode=restricted`):

1. `SELECT * FROM customers;` → returns the seeded rows.
2. `INSERT ...` / `DELETE ...` → both rejected with `Error validating query: ...` — a **second, independent layer**: postgres-mcp's own restricted-mode validator refuses the write before it reaches Postgres, on top of (not instead of) the `mcp_readonly` grant proven above.
3. Quirk: postgres-mcp reports these validation failures as a normal successful tool result (`isError: false`) with the error text embedded in the content — a caller that only checks `isError` will miss the failure.

`uvx postgres-mcp` currently fails locally (`ModuleNotFoundError: No module named 'mcp.server.fastmcp'`, confirmed real upstream bug) and there's no `npm`/`npx` path either — Docker is the only working way to run it. Tracked in `NEXTME.md`.

**`dbtools`** (`googleapis/genai-toolbox`, generic, driven by `tools.yaml`) — one server fronting all three engines:

1. Fixed tools: `query-customers` (Postgres), `query-products` (MySQL), `query-employees` (MSSQL) → each returns seeded rows. `insert-customer` / `delete-product` → both rejected, `isError: true`, underlying DB error surfaced verbatim.
2. Ad-hoc tools (`postgres-execute-sql` / `mysql-execute-sql` / `mssql-execute-sql`) and introspection tools (`postgres-list-tables` / `postgres-list-schemas` / `mysql-list-tables` / `mssql-list-tables` — no `mssql-list-schemas` equivalent exists in `genai-toolbox`) → all confirmed working per engine.
3. dbtools has **no independent query-validation layer** of its own (unlike `pgquery`'s restricted-mode validator) — enforcement is entirely the `mcp_readonly` grant. Ad-hoc tools are a deliberate tradeoff: they let a caller run any statement the grant permits, not just a hardcoded query — use the fixed-statement tools where the query is known ahead of time.

**`mysql-mcp`** (`benborla/mcp-server-mysql`, dedicated MySQL, single `mysql_query` tool):

1. `SELECT * FROM products;` → returns the seeded rows.
2. `INSERT ...` → rejected. **Second independent layer**: write operations are gated by env flags (`ALLOW_INSERT_OPERATION` etc.), explicitly left `false` in `.env` — note the locally-built image's own Dockerfile bakes these to `true` by default, so this override is load-bearing, not redundant.

**`mssql-mcp`** (`JexinSam/mssql_mcp_server`, dedicated MSSQL, `query_sql` + `execute_sql` tools):

1. `query_sql` with `SELECT * FROM employees;` → returns the seeded rows.
2. `query_sql` with an INSERT → rejected before it reaches the DB. **Second independent layer**: `query_sql` regex-gates to `SELECT`/`WITH`/`SHOW` only (verified against source, not just docs).
3. `execute_sql` is exposed separately, unrestricted, per the server's own design — not gated further by this stack.

## Dual-client verification

**Claude Code** — confirmed working through real `claude -p` CLI sessions (not just the protocol probes above), pointed at this project's own `.mcp.json`, scoped per-server via `--allowedTools mcp__<server>`:

```bash
docker compose up -d
claude -p "Using the pgquery MCP tool, SELECT * FROM customers, then try an INSERT and report what happened." --allowedTools mcp__pgquery
```

All four servers confirmed working this way — see `scripts/smoke_test.py`'s Tier 3 for the automated version (one plain-English question per server, run live). One thing worth knowing: `claude -p` (one-shot mode) left the MCP servers' Docker containers running after the CLI process exited, rather than cleaning them up — not a correctness problem, but `docker ps` / `docker rm -f` afterward if you drive this project the same way.

**VS Code** — two separate integration paths, both wired up in this repo:

- **Agent Host** reads root `.mcp.json` directly — confirmed empirically (disabling `.mcp.json` disabled VS Code's available servers too). Works with zero extra config.
- **Classic Copilot Chat "Agent Mode"** panel reads `.vscode/mcp.json` specifically (root key `servers`, not `mcpServers`) — added as a backward-compatible safety net, mirroring `.mcp.json`'s servers exactly.

Actually driving a query through either VS Code path still needs a human at the keyboard (no VS Code automation available in this environment) — not verified end-to-end. If you want this closed out, open this project in VS Code and confirm the same queries from the TL;DR work.

## Smoke test

`scripts/smoke_test.py` is a 3-tier check, run against the live stack:

1. **DB health** — each container's own Docker healthcheck, no MCP involved.
2. **Direct SQL sanity + MCP protocol-level** — one raw SQL statement per engine via the DB's own CLI client (no MCP), plus every deterministic, hand-picked MCP tool call documented above.
3. **Agent-driven natural-language query** — a live `claude -p` session per server, asked a plain-English question, asserting on the final answer. Proves the agent can translate text → SQL → tool call → answer, not just that a server responds when told exactly which tool to call. Needs `claude` installed and authenticated; set `SMOKE_TEST_SKIP_AGENT=1` to skip it for a faster routine run.

```bash
docker compose up -d
python3 scripts/smoke_test.py
```

Expected output (21 checks, all `[PASS]`):

```
=== Tier 1: DB health (Docker healthcheck, no MCP) ===
[PASS] postgres container healthy
...
=== Tier 3: Agent-driven natural-language query (live `claude` session) ===
[PASS] mssql-mcp: agent answers a plain-English employee question
```

## Credentials

`.env` is the single source of truth for every MCP server's credentials — no other file to check or keep in sync.

- `.mcp.json`'s Docker-based entries all pass `--env-file .env` to `docker run`, so Docker injects `.env`'s variables straight into each container.
- `pgquery` reads `DATABASE_URI` directly; `mysql-mcp` and `mssql-mcp` read their own upstream-defined var names (`MYSQL_*`, `MSSQL_*`).
- `dbtools` reads `tools.yaml`, where each source's `user`/`password` are `${VAR}` placeholders — `genai-toolbox` resolves these from its own environment natively.
- `tools.yaml` is a real, tracked file (no `.example` copy step) — it's already correct as checked in.
- All values here are throwaway, seeded fresh on every `docker compose up` (this is a disposable POC stack) — nothing to invent or protect.

## Tear down

```bash
docker compose down
```
