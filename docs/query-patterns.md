# Query patterns — building useful, safe database tools

Practical notes on structuring query capability for an MCP database server, and what's
already available but unused in this stack's 4 servers.

## Fixed vs. ad-hoc: use both, layered

- **Fixed, parameterized statements** for known/repeated questions — reviewable, safe by
  construction, cheap to reason about. This repo's `query-customers`, `query-products`, etc.
- **Ad-hoc SQL** for the long tail — necessary for a genuinely useful tool, but only as safe
  as its enforcement layer (see below).
- Real systems use both: a curated set of fixed tools for anything repeated or high-stakes,
  ad-hoc as the escape hatch for everything else. Don't try to enumerate every fixed query
  up front — grow the fixed set from what the ad-hoc path actually gets asked.

## Extend capability via visibility, not more raw access

The lever that actually improves ad-hoc query quality is **schema visibility**, not looser
permissions. A model writes better SQL when it can call an introspection tool first
(`list_tables`, `get_object_details`) than when it's guessing column names from a table name
alone. Growing the fixed-statement list indefinitely doesn't scale; giving the model tools to
discover the schema itself does.

## What's already available, unused, in this stack

Checked against source, not docs. All read-only / safe to enable.

**`pgquery` (postgres-mcp)** — 9 tools total, this repo only exercises `execute_sql`:

| Tool | Adds | Needs |
|---|---|---|
| `list_schemas` / `list_objects` / `get_object_details` | real schema introspection | nothing extra |
| `analyze_db_health` | 7 catalog-level health checks | nothing extra |
| `analyze_query_indexes` | index advice for a supplied query list | nothing extra |
| `explain_query` | EXPLAIN / EXPLAIN ANALYZE | plain mode works; hypothetical-index mode needs HypoPG (not installed) |
| `analyze_workload_indexes`, `get_top_queries` | workload-driven index/query advice | `pg_stat_statements` (not enabled) — also pointless without real traffic history |

**`dbtools` (genai-toolbox)** — wires 4 kinds/engine today; full inventory is 24 (postgres) /
10 (mysql) / 3 (mssql). Worth adding for this toy schema:

- Postgres: `postgres-list-indexes`, `postgres-list-sequences`, `postgres-get-column-cardinality`
- MySQL: `mysql-get-query-plan`, `mysql-list-tables-missing-unique-indexes`
- MSSQL: nothing left — only 3 kinds exist for MSSQL in genai-toolbox, all 3 already wired. A
  real, structural coverage gap vs. Postgres/MySQL, not a config oversight.

Everything else across all three engines (active queries, locks, replication stats, query
stats, table/database stats, publications, tablespaces, roles, extensions) needs either a
real workload history or objects (views/triggers/procs) this toy schema doesn't have — not
useful here, will be if this stack ever points at a non-toy database.

**`mysql-mcp` (benborla)** — table listing is exposed as an MCP *resource*
(`mysql://tables`, one resource per table), not a tool — a different protocol primitive this
stack doesn't otherwise use. Worth knowing if a client's UI treats resources differently from
tools.

**`mssql-mcp` (JexinSam)** — actually ships a `list_tables` tool (`INFORMATION_SCHEMA.TABLES`)
and a `mssql://{schema}/{table}/data` resource (first 100 rows) — undocumented in this repo
until now.

## Guardrails that matter in practice

- Read-only DB role (`mcp_readonly`) as the floor — every server here has it regardless of
  its own claims.
- A second, independent validator where the server offers one (`pgquery`'s
  `--access-mode=restricted`, `mysql-mcp`'s `ALLOW_*_OPERATION` flags, `mssql-mcp`'s
  `query_sql` regex gate) — don't rely on the DB grant alone if a stronger layer exists.
- Row/result limits on ad-hoc tools, once this stack points at non-toy data.
- Fixed statements as the trusted path for anything repeated or high-stakes; ad-hoc for
  everything else, with introspection tools available so the model isn't guessing schema.
