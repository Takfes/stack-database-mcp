# Query patterns

How production text-to-SQL / "chat with your database" systems handle complex queries, and
what that means for extending this stack past its current fixed statements. Researched, not
guessed — see sources.

## The finding: raw LLM-against-schema doesn't scale, semantic layers do

Free-form SQL generation against an undecorated schema is a weak pattern at any real
complexity:

- Spider 2.0 (the current enterprise text-to-SQL benchmark) is dramatically harder than its
  predecessor: GPT-4o scores **86.6%** on Spider 1.0 but only **10.1%** on Spider 2.0
  ([Spider 2.0 leaderboard](https://spider2-sql.github.io/)).
- A dbt-cited study: GPT-4 zero-shot raw SQL against enterprise databases scored **16.7%**
  accuracy; adding a knowledge-graph/semantic layer raised that to **54.2%**; dbt's own
  Semantic Layer measured **83%** on a subset of aggregation questions without heavy joins
  ([dbt Labs](https://www.getdbt.com/blog/semantic-layer-as-the-data-interface-for-llms)).
- The practical failure mode differs, not just the accuracy: *"with text-to-SQL, failure looks
  like a plausible but incorrect answer; with a semantic layer, failure looks like an error
  message"* ([Atlan](https://atlan.com/know/ai-agent/data-for-ai/text-to-sql-for-enterprise/)).

Production systems converge on three layers working together, not one technique alone:

1. **A semantic/metrics layer** for anything that must be reliably correct.
2. **Retrieval of known-good examples**, not a hand-maintained list, for the long tail.
3. **Execution-guided self-correction** as a safety net for whatever's still generated ad hoc.

## 1. Semantic layer — define joins/business logic once, query it by name

Snowflake Cortex Analyst, dbt's MetricFlow, and WrenAI all center on the same idea: a
YAML/DSL file defines logical tables, dimensions, metrics, and relationships once; the agent
asks for a metric or dimension by name instead of re-deriving joins per question.

- Snowflake Cortex Analyst's semantic model: tables, dimensions, facts, metrics,
  relationships, plus sample queries the LLM is shown directly
  ([Snowflake docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)).
- dbt MetricFlow: *"agents ask for a metric by name and receive proven SQL"* — governed,
  versioned, same answer everywhere
  ([dbt Labs](https://www.getdbt.com/blog/open-source-metricflow-governed-metrics)).
- WrenAI's open-source equivalent: a "Modeling Definition Language" capturing business
  semantics, metric definitions, and joins ([getwren.ai/oss](https://www.getwren.ai/oss)).

This repo's `tools.yaml` fixed statements are a small, unparameterized instance of this
pattern — each one hardcodes a join/filter once instead of leaving the model to reconstruct it.

## 2. Extend coverage via retrieval, not a growing hardcoded list

The realistic way to go past "the examples I wrote" is a **vector-indexed example bank**, not
manually adding more fixed queries forever:

- Vanna.ai trains on DDL + docs + example question→SQL pairs, all stored in a vector store;
  at query time it retrieves the closest matches and injects them as few-shot examples
  ([Vanna via Qdrant docs](https://qdrant.tech/documentation/frameworks/vanna-ai/)).
- Same pattern described generally as an "Example Bank": verified Q&A→SQL pairs, top-k
  retrieved by similarity to the new question, injected into the prompt — scales because
  retrieval picks the relevant few, not because someone pre-wrote every case
  ([Dynamic Few-Shot Prompting](https://medium.com/@fathir.majeed/agentic-text-to-sql-chatbot-with-dynamic-few-shot-prompting-1349b1a2fece)).

This repo's `QUERIES.md` is the raw material for exactly this — a growing set of verified
question→query pairs. The retrieval/indexing layer is what's missing to make it scale past a
POC; not needed at this size, but the direction to grow in if the fixed-statement list starts
feeling limiting.

## 3. Execution-guided self-correction as the fallback's fallback

For whatever still goes through ad-hoc generation: generate → execute → on error, feed the
error message back to the model → retry, bounded iterations. This is the mechanism behind
DIN-SQL (55.9% execution accuracy on BIRD) and newer work like LitE-SQL
([DIN-SQL](https://arxiv.org/abs/2304.11015),
[LitE-SQL](https://arxiv.org/html/2510.09014v1)). `dbtools`' ad-hoc tools already return the
underlying DB error verbatim on failure — the raw material for this loop is present; the
retry loop itself is a client-side (agent) behavior, not something this stack needs to build.

## What this means here, concretely

- Fixed statements in `tools.yaml` = the trusted, governed path. Keep using them for anything
  repeated or where a wrong answer matters.
- `QUERIES.md` = the seed of an example bank. Growing it is the right instinct; formal
  retrieval only pays off once it's too large to eyeball.
- Ad-hoc SQL = the long tail, always scoped to the read-only grant, always the fallback.

## Guardrails

- Read-only DB role as the floor, always.
- A second independent validator where the server offers one (`pgquery` restricted mode,
  `mysql-mcp`'s `ALLOW_*` flags, `mssql-mcp`'s regex gate).
- Row/result limits on ad-hoc tools once this points at non-toy data.
