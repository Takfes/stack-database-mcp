# Vendor/flavor-specific MCP server research — MySQL & MSSQL

Research deliverable for issue [#7](https://github.com/Takfes/stack-database-mcp/issues/7)
(sub-issue of [#8](https://github.com/Takfes/stack-database-mcp/issues/8)). No code changes
accompany this document — see [Recommendations](#recommendations) for why.

## Method

For each engine: searched GitHub + npm/PyPI for MCP servers dedicated to that single engine
(generic multi-engine servers like `dbtools`, which this repo already uses, don't count as
candidates). For every credible hit, verified against the actual source rather than README
claims — repo activity (`pushed_at`), license, star count/contributor count as an activity/health
proxy, and the real tool definitions read from source to confirm ad-hoc query and/or
introspection capability, and how (or whether) read-only is enforced. Same diligence pattern
`indie-marketplace`'s `bundles.yaml` already applied to `azkusto` (picked over
`pab1it0/adx-mcp-server` for lacking a read-only layer) and `last30days`.

All repo metadata below was pulled live via the GitHub API on 2026-08-20.

## MySQL

| Candidate | Repo | License | Stars | Last push | Verdict |
|---|---|---|---|---|---|
| **mcp-server-mysql** | [benborla/mcp-server-mysql](https://github.com/benborla/mcp-server-mysql) | MIT | 2,059 | 2026-07-27 | **Document as alternative** |
| mysql_mcp_server | [designcomputer/mysql_mcp_server](https://github.com/designcomputer/mysql_mcp_server) | MIT | 1,362 | 2026-08-02 | Discard (no differentiation from `dbtools`) |
| mysql-mcp-server (Oracle) | [oracle/mcp](https://github.com/oracle/mcp/blob/main/src/mysql-mcp-server/README.md) | UPL-1.0 | 426 | 2026-08-14 | Discard (wrong shape) |

### benborla/mcp-server-mysql — verified

- Single ad-hoc tool, `mysql_query`, accepting an arbitrary SQL string
  ([`index.ts:340`](https://github.com/benborla/mcp-server-mysql/blob/main/index.ts#L340)).
- Introspection exposed as MCP *resources* rather than tools: a `mysql://tables` listing plus
  one resource per table backed by `INFORMATION_SCHEMA` queries
  ([`index.ts:220-245`](https://github.com/benborla/mcp-server-mysql/blob/main/index.ts#L220-L245)).
- Read-only enforcement is real and app-level, not just a README claim: `ALLOW_INSERT_OPERATION`,
  `ALLOW_UPDATE_OPERATION`, `ALLOW_DELETE_OPERATION`, and `ALLOW_DDL_OPERATION` all default to
  `false` and only flip on when the corresponding env var is the literal string `"true"`
  ([`src/config/index.ts:69-76`](https://github.com/benborla/mcp-server-mysql/blob/main/src/config/index.ts#L69-L76)).
  `src/db/permissions.ts` enforces this per operation, and even lets individual schemas override
  the global default (`SCHEMA_INSERT_PERMISSIONS` etc.) — a second independent safety layer on
  top of whatever the connecting MySQL user is granted, the same shape as this repo's `pgquery`
  `--access-mode=restricted` flag.
- Actively maintained: 2,059 stars, MIT, pushed within the last month at time of writing.

**This is a stronger read-only story than `dbtools` currently has for MySQL** — `dbtools`' MySQL
coverage relies entirely on the `mcp_readonly` grant (see this repo's README, "dbtools has no
independent query-validation layer of its own"), where `mcp-server-mysql` adds an opt-in
app-level gate in front of that. It's a credible, verifiable, well-adopted candidate.

### designcomputer/mysql_mcp_server — verified, discarded

`execute_sql` is explicitly documented and coded to accept `SELECT, DML (INSERT/UPDATE/DELETE),
SHOW, DESCRIBE, and ad-hoc queries` with `readOnlyHint=False`
([`server.py:302,318`](https://github.com/designcomputer/mysql_mcp_server/blob/main/src/mysql_mcp_server/server.py#L302)).
There is no app-level write gate — enforcement is entirely the connecting DB user's grants,
identical in posture to `dbtools`. Legitimate, active (MIT, 1,362 stars, pushed 2026-08-02), but
offers nothing `dbtools` doesn't already provide, so it isn't worth documenting as an alternative.

### oracle/mcp `mysql-mcp-server` — verified, discarded

Oracle's own official repo, but the README states plainly: *"This MCP server is not intended for
production use but as a proof of concept."* Its ~14 tools are overwhelmingly MySQL
HeatWave/GenAI-feature oriented (vector embeddings, RAG, OCI Object Storage integration) rather
than plain query/introspection, and no read-only enforcement is documented. Wrong shape for this
repo's use case even though it's an active, official Oracle project.

## MSSQL

| Candidate | Repo | License | Stars | Last push | Verdict |
|---|---|---|---|---|---|
| **mssqlclient-mcp-server** | [aadversteeg/mssqlclient-mcp-server](https://github.com/aadversteeg/mssqlclient-mcp-server) | MIT | 41 | 2026-06-05 | **Document as alternative** |
| mcp-sqlserver | [trainerroad/mcp-sqlserver](https://github.com/trainerroad/mcp-sqlserver) | MIT | 7 | 2026-03-04 | Document as reference design only (too immature to adopt) |
| mssql_mcp_server | [RichardHan/mssql_mcp_server](https://github.com/RichardHan/mssql_mcp_server) | MIT | 386 | 2025-11-02 | Discard (no differentiation, stale) |
| MssqlMcp (Microsoft, dotnet sample) | [Azure-Samples/SQL-AI-samples](https://github.com/Azure-Samples/SQL-AI-samples) | MIT | 330 | 2026-06-03 | **Discard — retracted by Microsoft** |
| SQL MCP Server (Data API builder) | [azure/data-api-builder](https://learn.microsoft.com/en-us/azure/data-api-builder/mcp/overview) | MIT | — | active | Discard (out of scope: generic multi-engine, no ad-hoc SQL) |

### Microsoft's on-prem sample was pulled as unsafe — verified

The most prominent search hit for an "official Microsoft MSSQL MCP server" was
`Azure-Samples/SQL-AI-samples/MssqlMcp/dotnet`, previously exposing `ListTables`, `DescribeTable`,
`CreateTable`, `DropTable`, `InsertData`, `ReadData`, `UpdateData` — full CRUD/DDL, not read-only.
That folder no longer exists in the repo: it was removed in
[PR #96, "Removed unsafe MCP sample"](https://github.com/Azure-Samples/SQL-AI-samples/pull/96)
(merged 2026-06-03), whose description reads: *"This demo has been scrubbed from our blogs, but
this folder continues to pop up for customers leading them down the wrong road for developing MCP
solutions."* Confirmed via the repo's own commit history against the `MssqlMcp` path, not a
secondhand claim. This rules the sample out categorically — Microsoft itself disowns it.

### Microsoft's current official offering is out of scope — verified

Microsoft's actual current product in this space is **SQL MCP Server**, a feature of
[Data API builder](https://learn.microsoft.com/en-us/azure/data-api-builder/mcp/overview) (open
source, MIT, actively developed, production-oriented with RBAC/caching/OpenTelemetry). Two
disqualifiers, both confirmed from Microsoft's own docs:

1. It's explicitly multi-engine — the same `dab-config.json` targets MSSQL, PostgreSQL, MySQL,
   and Cosmos DB — making it categorically the same kind of tool as `dbtools`, not a
   vendor/flavor-specific alternative to it.
2. It intentionally has no ad-hoc SQL execution. Tools (`describe_entities`, `create_record`,
   `read_records`, `update_record`, `delete_record`, `execute_entity`, `aggregate_records`)
   operate only against tables/views/procedures pre-declared in config, and the docs explicitly
   reject NL2SQL/free-form querying by design. It doesn't cover the "ad-hoc" capability this
   research is checking for.

### aadversteeg/mssqlclient-mcp-server — verified

- Exposes `execute_query` (ad hoc SQL) plus `list_tables`, `get_table_schema`, `list_databases`
  for introspection, and a stored-procedure toolset (`list_stored_procedures`,
  `get_stored_procedure_definition`, `execute_stored_procedure`), confirmed against the README
  and the multi-project .NET solution layout (`Core.Application`,
  `Core.Infrastructure.McpServer`, `Core.Infrastructure.SqlClient`, plus unit-test projects for
  each).
- Read-only posture is an allowlist-of-capabilities model, not a query-content validator: query
  and stored-procedure *execution* tools are disabled by default at the MCP tool-registration
  layer and only appear once `DatabaseConfiguration__EnableExecuteQuery=true` (and the equivalent
  flag for procedures) is set explicitly. That's stricter than "read-only" — by default there's no
  ad-hoc query capability at all, so matching this repo's read+block-write pattern needs deliberate
  configuration rather than an out-of-the-box toggle.
- Supports on-prem SQL Server (including Windows Authentication) and Azure SQL. MIT, 41 stars,
  pushed 2026-06-05 — small but actively maintained, with real test coverage.

### trainerroad/mcp-sqlserver — verified, documented but not adopted

The strongest *design* found for MSSQL, verified directly in source:

- `connection.ts` hardcodes `readOnlyIntent: true`
  ([`src/connection.ts:26`](https://github.com/trainerroad/mcp-sqlserver/blob/main/src/connection.ts#L26)),
  i.e. SQL Server's native `ApplicationIntent=ReadOnly`, which routes to read replicas where
  available — a connection-level guarantee, not just an app-level check.
- `security.ts` implements a real query validator: queries must start with one of
  `SELECT/WITH/SHOW/DESCRIBE/EXPLAIN`, then are scanned for a forbidden-keyword list
  (`INSERT/UPDATE/DELETE/DROP/CREATE/ALTER/TRUNCATE/EXEC/EXECUTE/SP_/XP_/OPENROWSET/
  OPENDATASOURCE/BULK/MERGE/GRANT/REVOKE/DENY`), plus basic injection-pattern heuristics
  ([`src/security.ts`](https://github.com/trainerroad/mcp-sqlserver/blob/main/src/security.ts)).

This is exactly the second-independent-layer pattern this repo already values (`pgquery`'s
`--access-mode=restricted`). But the project's own history disqualifies it from adoption: it was
created 2026-03-03, every commit lands on a single day (2026-03-03/04), there has been no activity
since (5+ months stale at time of writing), it has 7 stars, and both contributors appear to be
from the same small company (TrainerRoad) releasing an internal tool. Real code, real design,
too thin a track record to depend on. Worth citing as a reference pattern if `dbtools`' MSSQL
coverage ever needs an app-level validator of its own.

### RichardHan/mssql_mcp_server — verified, discarded

Single tool executes arbitrary SQL including non-`SELECT` statements (it commits the transaction
and returns the affected-row count for writes) —
([`server.py:218-260`](https://github.com/RichardHan/mssql_mcp_server/blob/main/src/mssql_mcp_server/server.py#L218-L260)).
No app-level read-only gate; enforcement is entirely the connecting DB user's grants, the same
posture `dbtools` already has. MIT, 386 stars, but last pushed 2025-11-02 — noticeably staler than
the other candidates checked. No reason to prefer it over `dbtools`.

## Recommendations

| Engine | Recommendation | Candidate |
|---|---|---|
| MySQL | **Document as alternative** | `benborla/mcp-server-mysql` — verified opt-in app-level write gate, stronger read-only story than `dbtools` currently has for MySQL, active and well-adopted (2,059 stars) |
| MSSQL | **Document as alternative** | `aadversteeg/mssqlclient-mcp-server` — the healthiest dedicated MSSQL candidate found (active, MIT, tested); `trainerroad/mcp-sqlserver`'s validator design is worth referencing separately even though the project itself is too immature to adopt as-is |

Per the parent spec (issue [#8](https://github.com/Takfes/stack-database-mcp/issues/8)), neither
finding replaces `dbtools`' coverage of its engine. The architecture stays **one generic `dbtools`
server, three engines** as the default; this document exists so the alternative is known and
traceable if a future explicit decision revisits it. No changes were made to `tools.yaml.example`,
`docker-compose.yml`, or `.mcp.json` as part of this research.
