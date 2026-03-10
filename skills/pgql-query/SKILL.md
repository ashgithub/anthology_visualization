---
name: pgql-query
description: Use this skill when the user asks for Oracle property graph queries in Oracle's hybrid SQL/PGQL style.
---

# pgql-query

## Overview
Generate one Oracle property graph query in the Oracle hybrid SQL/PGQL style.

## Instructions
1. Treat this skill as the authoritative mode for Oracle property graph queries.
2. Use [the PGQL reference](references/REFERENCE.md) for rules and examples.
3. Use [the graph schema summary](assets/schema_summary.md) for graph names and domain context.
4. Return exactly one query and nothing else.
5. Important Oracle rule: when using Oracle property graph query syntax, `MATCH` must appear inside `GRAPH_TABLE(...)`. Do not write `FROM MATCH ...`.
6. Important Oracle rule: include `COLUMNS(...)` inside `GRAPH_TABLE(...)`.

## Critical rules
- Use Oracle SQL `GRAPH_TABLE(...)` syntax for graph queries.
- Keep `MATCH` inside `GRAPH_TABLE(...)`.
- Always include a `COLUMNS(...)` clause.
- Do not use `PGQL_QUERY()`.
- Keep the query read-only.
- Use only graph names, labels, edge names, and properties defined in the schema summary.
- Do not invent schema terms.
- Prefer a valid, schema-correct query over a speculative one.

## Query construction checklist
1. Identify the correct graph name from the schema summary.
2. Identify the required vertex labels, edge labels, and properties from the schema summary.
3. Build the graph pattern inside `MATCH`.
4. Put graph-property filters inside `GRAPH_TABLE(...)` when they apply to graph variables.
5. Project every field needed by the outer query in `COLUMNS(...)`.
6. Apply `ORDER BY`, `GROUP BY`, and row limiting to projected columns.
7. Return exactly one query and no explanation.
