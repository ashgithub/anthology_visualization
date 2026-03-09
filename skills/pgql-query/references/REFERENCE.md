# PGQL query reference

## Goal
Generate Oracle Property Graph Query Language (PGQL) queries only.

## Rules
- Return exactly one PGQL query.
- Do not return Oracle SQL.
- Do not use GRAPH_TABLE.
- Use graph MATCH patterns and graph semantics.
- Keep the query read-only.

## Schema
See [the graph schema summary](../assets/schema_summary.md).
