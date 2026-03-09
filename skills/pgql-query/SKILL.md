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
