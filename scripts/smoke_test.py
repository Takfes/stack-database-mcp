#!/usr/bin/env python3
"""
Trivial smoke test for the two bundled database MCP servers, run through the
real MCP protocol (not a raw DB client) against the running stack-database-mcp
containers. Requires `docker compose up -d` to already be running.

pgquery : proves SELECT works and INSERT is rejected in --access-mode=restricted.
dbtools : proves one server, one tools.yaml, queries Postgres, MySQL, and MSSQL
          via both the fixed-statement tools and the ad-hoc/introspection tools.
"""
import json
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


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


def main():
    ok = True

    select_result, insert_result = run_server(
        [
            "-e", "DATABASE_URI=postgresql://mcp_readonly:readonly@postgres:5432/appdb",
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
        customers_result, products_result,
        pg_adhoc_result, mysql_adhoc_result, mssql_adhoc_result,
        pg_tables_result, mysql_tables_result, mssql_tables_result,
    ) = run_server(
        [
            "-v", f"{ROOT / 'tools.yaml'}:/tools.yaml:ro",
            "us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:latest",
            "--stdio", "--config", "/tools.yaml",
        ],
        [
            ("query-customers", {}),
            ("query-products", {}),
            ("postgres-execute-sql", {"sql": "SELECT * FROM customers;"}),
            ("mysql-execute-sql", {"sql": "SELECT * FROM products;"}),
            ("mssql-execute-sql", {"sql": "SELECT * FROM employees;"}),
            ("postgres-list-tables", {}),
            ("mysql-list-tables", {}),
            ("mssql-list-tables", {}),
        ],
    )
    ok &= check("dbtools: queries Postgres (customers)", "Ada Lovelace" in result_text(customers_result))
    ok &= check("dbtools: queries MySQL (products)", "Widget" in result_text(products_result))
    ok &= check("dbtools: ad-hoc execute-sql on Postgres", "Ada Lovelace" in result_text(pg_adhoc_result))
    ok &= check("dbtools: ad-hoc execute-sql on MySQL", "Widget" in result_text(mysql_adhoc_result))
    ok &= check("dbtools: ad-hoc execute-sql on MSSQL (connectivity)", "Katherine Johnson" in result_text(mssql_adhoc_result))
    ok &= check("dbtools: schema introspection on Postgres", "customers" in result_text(pg_tables_result))
    ok &= check("dbtools: schema introspection on MySQL", "products" in result_text(mysql_tables_result))
    ok &= check("dbtools: schema introspection on MSSQL", "employees" in result_text(mssql_tables_result))

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
