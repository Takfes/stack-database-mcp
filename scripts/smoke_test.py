#!/usr/bin/env python3
"""
Three-tier smoke test for stack-database-mcp, run against the running containers
(`docker compose up -d` must already be up, and `tools.yaml` must exist locally).

Tier 1 — DB health: each container's own Docker healthcheck, no MCP involved.
Tier 2 — Direct SQL sanity: one raw SQL statement per engine via the DB's own CLI
          client, no MCP involved. Also covers each MCP server's protocol-level
          behaviour (SELECT works, writes rejected, ad-hoc/introspection tools) —
          deterministic, hand-picked tool calls, not natural language.
Tier 3 — Agent-driven natural-language query: drives a live `claude` CLI session
          per MCP server, asking a plain-English question and asserting on the
          final answer. Proves the agent can translate text -> SQL -> tool call
          -> answer, not just that a server responds correctly when told exactly
          which tool to call. Requires `claude` to be installed and authenticated;
          set SMOKE_TEST_SKIP_AGENT=1 to skip this tier for a faster routine run.
"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).parent.parent
NETWORK = "stack-database-mcp_default"


def send(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def recv(proc):
    line = proc.stdout.readline()
    while line.strip() == "":
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("EOF from server")
    return json.loads(line)


def run_server(docker_args, calls):
    """Start an MCP server over stdio, run the handshake, then a list of
    (tool_name, arguments) calls, returning their results."""
    name = f"smoke-{uuid.uuid4().hex[:8]}"
    proc = subprocess.Popen(
        ["docker", "run", "-i", "--rm", "--name", name, "--network", NETWORK, *docker_args],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=1,
    )
    try:
        send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "smoke-test", "version": "1.0"}}})
        recv(proc)
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        results = []
        for i, (tool, args) in enumerate(calls, start=2):
            send(proc, {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                        "params": {"name": tool, "arguments": args}})
            results.append(recv(proc))
        return results
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def result_text(result):
    content = result.get("result", {}).get("content", [])
    return " ".join(c.get("text", "") for c in content)


def docker_health(container):
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", container],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def run_sql(container, *cli_args):
    result = subprocess.run(["docker", "exec", container, *cli_args], capture_output=True, text=True)
    return result.stdout + result.stderr


def run_agent_query(server, question):
    """Ask a live `claude` CLI session a natural-language question, run from ROOT
    so it picks up this project's own .mcp.json. Scoped to just the MCP server
    under test via --allowedTools, rather than bypassing permissions entirely."""
    result = subprocess.run(
        ["claude", "-p", question, "--allowedTools", f"mcp__{server}"],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )
    return result.stdout


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


def tier1_db_health():
    print("=== Tier 1: DB health (Docker healthcheck, no MCP) ===")
    ok = True
    ok &= check("postgres container healthy", docker_health("stack-database-mcp-postgres-1") == "healthy")
    ok &= check("mysql container healthy", docker_health("stack-database-mcp-mysql-1") == "healthy")
    ok &= check("mssql container healthy", docker_health("stack-database-mcp-mssql-1") == "healthy")
    return ok


def tier2_direct_sql():
    print("=== Tier 2a: Direct SQL sanity (raw DB client, no MCP) ===")
    ok = True
    pg_out = run_sql("stack-database-mcp-postgres-1", "psql", "-U", "mcp_readonly", "-d", "appdb",
                      "-c", "SELECT * FROM customers;")
    ok &= check("postgres: SELECT returns seeded customers", "Ada Lovelace" in pg_out)

    mysql_out = run_sql("stack-database-mcp-mysql-1", "mysql", "-uroot", "-padmin", "appdb",
                         "-e", "SELECT * FROM products;")
    ok &= check("mysql: SELECT returns seeded products", "Widget" in mysql_out)

    mssql_out = run_sql("stack-database-mcp-mssql-1", "/opt/mssql-tools18/bin/sqlcmd",
                         "-S", "localhost", "-U", "mcp_readonly", "-P", "Readonly123!", "-C",
                         "-d", "appdb", "-Q", "SELECT * FROM employees;")
    ok &= check("mssql: SELECT returns seeded employees", "Katherine Johnson" in mssql_out)
    return ok


def tier2_mcp_protocol():
    print("=== Tier 2b: MCP protocol-level (deterministic, hand-picked tool calls) ===")
    ok = True

    select_result, insert_result = run_server(
        [
            "--env-file", f"{ROOT / '.env'}",
            "crystaldba/postgres-mcp", "--access-mode=restricted", "--transport=stdio",
        ],
        [
            ("execute_sql", {"sql": "SELECT * FROM customers;"}),
            ("execute_sql", {"sql": "INSERT INTO customers (name, email) VALUES ('x', 'x@x.com');"}),
        ],
    )
    ok &= check("pgquery: SELECT returns seeded rows", "Ada Lovelace" in result_text(select_result))
    ok &= check("pgquery: INSERT is rejected", "error" in result_text(insert_result).lower())

    (
        customers_result, products_result, employees_result,
        pg_adhoc_result, mysql_adhoc_result, mssql_adhoc_result,
        pg_tables_result, mysql_tables_result, mssql_tables_result,
        mysql_query_plan_result, mysql_missing_idx_result,
    ) = run_server(
        [
            "--env-file", f"{ROOT / '.env'}",
            "-v", f"{ROOT / 'tools.yaml'}:/tools.yaml:ro",
            "us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest",
            "--stdio", "--config", "/tools.yaml",
        ],
        [
            ("query-customers", {}),
            ("query-products", {}),
            ("query-employees", {}),
            ("postgres-execute-sql", {"sql": "SELECT * FROM customers;"}),
            ("mysql-execute-sql", {"sql": "SELECT * FROM products;"}),
            ("mssql-execute-sql", {"sql": "SELECT * FROM employees;"}),
            ("postgres-list-tables", {}),
            ("mysql-list-tables", {}),
            ("mssql-list-tables", {}),
            ("mysql-get-query-plan", {"sql_statement": "SELECT * FROM products;"}),
            ("mysql-list-tables-missing-unique-indexes", {}),
        ],
    )
    ok &= check("dbtools: queries Postgres (customers)", "Ada Lovelace" in result_text(customers_result))
    ok &= check("dbtools: queries MySQL (products)", "Widget" in result_text(products_result))
    ok &= check("dbtools: queries MSSQL (employees)", "Katherine Johnson" in result_text(employees_result))
    ok &= check("dbtools: ad-hoc execute-sql on Postgres", "Ada Lovelace" in result_text(pg_adhoc_result))
    ok &= check("dbtools: ad-hoc execute-sql on MySQL", "Widget" in result_text(mysql_adhoc_result))
    ok &= check("dbtools: ad-hoc execute-sql on MSSQL", "Katherine Johnson" in result_text(mssql_adhoc_result))
    ok &= check("dbtools: schema introspection on Postgres", "customers" in result_text(pg_tables_result))
    ok &= check("dbtools: schema introspection on MySQL", "products" in result_text(mysql_tables_result))
    ok &= check("dbtools: schema introspection on MSSQL", "employees" in result_text(mssql_tables_result))
    ok &= check("dbtools: mysql-get-query-plan explains a statement", "products" in result_text(mysql_query_plan_result).lower())
    ok &= check(
        "dbtools: mysql-list-tables-missing-unique-indexes runs clean (seeded tables are all keyed)",
        "error" not in result_text(mysql_missing_idx_result).lower(),
    )

    mysql_select_result, mysql_insert_result = run_server(
        ["--env-file", f"{ROOT / '.env'}", "stack-database-mcp-mysql-mcp:local"],
        [
            ("mysql_query", {"sql": "SELECT * FROM products;"}),
            ("mysql_query", {"sql": "INSERT INTO products (name) VALUES ('x');"}),
        ],
    )
    ok &= check("mysql-mcp: SELECT returns seeded rows", "Widget" in result_text(mysql_select_result))
    ok &= check("mysql-mcp: INSERT is rejected", "error" in result_text(mysql_insert_result).lower())

    mssql_select_result, mssql_insert_result = run_server(
        ["--env-file", f"{ROOT / '.env'}", "stack-database-mcp-mssql-mcp:local"],
        [
            ("query_sql", {"query": "SELECT * FROM employees;"}),
            ("query_sql", {"query": "INSERT INTO employees (name, title) VALUES ('x', 'x');"}),
        ],
    )
    ok &= check("mssql-mcp: query_sql SELECT returns seeded rows", "Katherine Johnson" in result_text(mssql_select_result))
    ok &= check("mssql-mcp: query_sql rejects non-SELECT", "error" in result_text(mssql_insert_result).lower())
    return ok


def tier3_agent_nl():
    if os.environ.get("SMOKE_TEST_SKIP_AGENT"):
        print("=== Tier 3: Agent-driven NL query — SKIPPED (SMOKE_TEST_SKIP_AGENT set) ===")
        return True

    print("=== Tier 3: Agent-driven natural-language query (live `claude` session) ===")
    ok = True
    ok &= check(
        "pgquery: agent answers a plain-English customer question",
        "Ada Lovelace" in run_agent_query("pgquery", "Using the pgquery MCP tool, list all customers."),
    )
    ok &= check(
        "dbtools: agent answers a plain-English MySQL question",
        "Widget" in run_agent_query("dbtools", "Using the dbtools MCP tool, list the products from the MySQL database."),
    )
    ok &= check(
        "mysql-mcp: agent answers a plain-English product question",
        "Widget" in run_agent_query("mysql-mcp", "Using the mysql-mcp MCP tool, list the products in the database."),
    )
    ok &= check(
        "mssql-mcp: agent answers a plain-English employee question",
        "Katherine Johnson" in run_agent_query("mssql-mcp", "Using the mssql-mcp MCP tool, list the employees in the database."),
    )
    return ok


def main():
    ok = True
    ok &= tier1_db_health()
    ok &= tier2_direct_sql()
    ok &= tier2_mcp_protocol()
    ok &= tier3_agent_nl()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
