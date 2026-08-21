# Dedicated per-flavor MCP servers — research

Which single-engine MCP servers exist for MySQL and MSSQL, and what's actually running in
this stack. `dbtools` (generic, multi-engine) stays the default for all three engines
regardless — this only tracks the vendor/flavor-specific alternative per engine, same as
`pgquery` is to Postgres.

## MySQL — adopted: `benborla/mcp-server-mysql`

| Candidate | License | Stars | Last push | Verdict |
|---|---|---|---|---|
| **benborla/mcp-server-mysql** | MIT | 2,059 | 2026-07-27 | **Adopted** |
| designcomputer/mysql_mcp_server | MIT | 1,362 | 2026-08-02 | Discard — no read-only gate, same posture as `dbtools` |
| oracle/mcp `mysql-mcp-server` | UPL-1.0 | 426 | 2026-08-14 | Discard — HeatWave/GenAI-feature focused, explicitly PoC-only, no read-only enforcement |

**Why**: real app-level write gate (`ALLOW_INSERT_OPERATION`/`ALLOW_UPDATE_OPERATION`/
`ALLOW_DELETE_OPERATION`/`ALLOW_DDL_OPERATION`, verified in source), independent of the DB
grant — the same second-layer pattern `pgquery` gives Postgres. Active, well-adopted.
**Caveat found during adoption**: the published Docker image bakes these flags to `true` by
default (contrary to the npm package's own documented safe default) — overridden explicitly
in this repo's `.env`, verified live that the override holds.

Tools: single ad-hoc `mysql_query`. Table listing is an MCP *resource* (`mysql://tables` +
one resource per table), not a tool — a different protocol primitive than every other server
in this stack.

## MSSQL — adopted: `JexinSam/mssql_mcp_server`

| Candidate | License | Stars | Last push | Verdict |
|---|---|---|---|---|
| **JexinSam/mssql_mcp_server** | MIT | 57 | 2026-08-16 | **Adopted** |
| aadversteeg/mssqlclient-mcp-server | MIT | 41 | 2026-06-05 | Not adopted — see note below |
| trainerroad/mcp-sqlserver | MIT | 7 | 2026-03-04 | Reference design only — best validator pattern found, but single-day commit history, stale 5+ months, too thin a track record |
| RichardHan/mssql_mcp_server | MIT | 386 | 2025-11-02 | Discard — no read-only gate, stale |
| Microsoft `MssqlMcp` (Azure-Samples, dotnet) | MIT | 330 | 2026-06-03 | Discard — Microsoft itself pulled it as unsafe (full CRUD/DDL, no read-only); see [PR #96](https://github.com/Azure-Samples/SQL-AI-samples/pull/96) |
| Microsoft SQL MCP Server (Data API builder) | MIT | — | active | Discard — multi-engine like `dbtools`, no ad-hoc SQL by design |

**Note on the mismatch**: the original research pass recommended `aadversteeg/mssqlclient-mcp-server`
as the healthiest dedicated MSSQL candidate. `JexinSam/mssql_mcp_server` was adopted instead
by explicit decision at ticket time, not because `aadversteeg` was found deficient —
`aadversteeg`'s query/procedure-execution tools are disabled by default at the MCP
registration layer (stricter than "read-only": no ad-hoc capability at all until explicitly
enabled), which is a real, valid design, just a different one than what got built.

**JexinSam, verified**: `query_sql` regex-gates to `SELECT`/`WITH`/`SHOW` only (checked
against source); `execute_sql` is exposed separately, unrestricted, per the server's own
design. Also ships a `list_tables` tool (`INFORMATION_SCHEMA.TABLES`) and a
`mssql://{schema}/{table}/data` resource (first 100 rows) — both undocumented in this repo
until now.

**Known upstream bug, worked around**: the Dockerfile never copies `README.md` into the
build context, but `pyproject.toml`'s hatchling backend requires it at build time — `pip
install .` fails on a stock clone. Fixed in this repo's vendored, pinned copy
(`docker/mssql-mcp/Dockerfile`) with a real `COPY README.md .` step. Tracked in `NEXTME.md`.

## Method

For each engine: searched GitHub for MCP servers dedicated to that single engine (generic
multi-engine servers don't count). For every credible hit, verified against source — not
README claims — for real tool definitions, ad-hoc/introspection capability, and how (or
whether) read-only is enforced. Repo metadata pulled live via the GitHub API.
