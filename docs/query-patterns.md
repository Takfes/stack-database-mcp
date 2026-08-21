# Query patterns

How to give an agent enough structure to build correct queries, and how to extend past the
fixed statements already in `tools.yaml`.

## Give the agent structure, not just SQL access

- **Bundle known-good queries.** `tools.yaml`'s fixed statements + `QUERIES.md` already are
  this — a discoverable library of tested queries, not ad-hoc guesses each time. Extend it by
  promoting an ad-hoc query into `tools.yaml` once it proves useful and gets repeated.
- **Parameterize before you multiply tools.** A fixed statement with a bound param
  (`WHERE id = ?`) covers a family of questions, not just one — cheaper than a new tool per
  variant.
- **Give schema context up front.** A short note per table (purpose, key relationships,
  gotchas) beats making the agent introspect from scratch every session. `tools.yaml`'s
  `description:` field on each tool is this mechanism already — keep it specific, not generic.
- **Real-world analog**: semantic/metrics layers (dbt Semantic Layer, Cube, LookML) centralize
  join/business logic once so every consumer — agent included — reuses the same definitions
  instead of re-deriving them per query. Same idea as the two bullets above, formalized at scale.

## Extending past fixed queries — cheapest first

1. Parameterize an existing fixed statement.
2. Add a new fixed statement to `tools.yaml` (a genuinely new question shape).
3. Ad-hoc SQL (`*-execute-sql`), scoped to the DB grant — fallback, not default.

## Guardrails

- Read-only DB role as the floor, always.
- A second independent validator where the server offers one (`pgquery` restricted mode,
  `mysql-mcp`'s `ALLOW_*` flags, `mssql-mcp`'s regex gate).
- Row/result limits on ad-hoc tools once this points at non-toy data.
- Fixed statements = trusted path for anything repeated/high-stakes; ad-hoc = the long tail only.
