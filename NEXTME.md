# NEXTME — Deferred / Future Work

Backlog items surfaced while building and verifying this stack. Not blocking — revisit each when relevant.

- **Revisit the database MCP servers, starting with pgquery's Docker-only install.** `pgquery` (`crystaldba/postgres-mcp`) only runs via `docker run` in this stack's `.mcp.json` — `uvx postgres-mcp` fails with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` (confirmed real upstream bug, not a cache issue — reproduced with `uvx --refresh`), and there's no `npm`/`npx` path at all (it's a Python package). Migrated from `indie-marketplace`'s NEXTME.md, where the finding was originally logged — that repo's `database` plugin ships the same Docker-only `pgquery` config as a result. Revisit periodically in both repos: watch upstream for the packaging fix, or accept Docker as a permanent prerequisite.
