# NEXTME — Deferred / Future Work

Backlog items surfaced while building and verifying this stack. Not blocking — revisit each when relevant.

## pgquery is Docker-only

- `crystaldba/postgres-mcp` only runs via `docker run` — `uvx postgres-mcp` fails with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` (confirmed real upstream bug, reproduced with `uvx --refresh`, re-reproduced 2026-08-21).
- No `npm`/`npx` path either — it's a Python package.
- Same finding logged in `indie-marketplace`'s NEXTME.md; that repo's `database` plugin ships the same Docker-only config as a result.
- Contrast: `dbtools` (`genai-toolbox`) is *not* Docker-only — ships standalone binaries too. Limitation is `pgquery`-specific.
- Revisit: watch upstream for the packaging fix, or accept Docker as permanent.

## mysql-mcp / mssql-mcp have no published image

- Neither `benborla/mcp-server-mysql` nor `JexinSam/mssql_mcp_server` publishes a Docker image — built locally by hand, not reproduced by `docker compose up`.
- `benborla`'s Dockerfile bakes in `ALLOW_INSERT_OPERATION=true`/`ALLOW_UPDATE_OPERATION=true` by default, contrary to its own README — overridden in `.env`, verified live.
- `JexinSam`'s Dockerfile never copies `README.md` into the build context, but the hatchling backend requires it — built from a locally patched clone (`COPY README.md .` added) instead.
- Revisit if either project publishes a real image or fixes these upstream.
