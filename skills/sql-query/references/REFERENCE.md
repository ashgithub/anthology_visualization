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

## Examples

### List substations by capacity
```sql
SELECT name, capacity_mva
FROM substations
ORDER BY capacity_mva DESC
```

### Join circuits to substations
```sql
SELECT c.circuit_name, s.name AS substation_name
FROM circuits c
JOIN substations s ON s.id = c.substation_id
ORDER BY s.name, c.circuit_name
```

### Find outages and root cause assets
```sql
SELECT o.incident_code, a.asset_id
FROM outages o
LEFT JOIN assets a ON a.id = o.root_cause_asset_id
ORDER BY o.start_time DESC
```
