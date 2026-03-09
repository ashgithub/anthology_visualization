# SQL query reference

## Goal
Generate traditional read-only Oracle SQL over relational tables and views.

## Rules
- Return exactly one Oracle SQL statement.
- Use standard relational SQL.
- Prefer explicit joins using documented foreign key relationships.
- Do not use GRAPH_TABLE.
- Do not use PGQL syntax.
- Do not write INSERT, UPDATE, DELETE, MERGE, DROP, ALTER, or TRUNCATE.
- Keep output executable as-is by the backend.

## Schema
See [the relational schema summary](../assets/schema_summary.md).
