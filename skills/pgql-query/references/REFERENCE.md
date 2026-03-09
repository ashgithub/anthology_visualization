# PGQL / Oracle property graph query reference

## Goal
Generate Oracle property graph queries in Oracle's hybrid SQL/PGQL style.

## Rules
- Return exactly one query.
- Use Oracle SQL `GRAPH_TABLE(...)` syntax for graph queries.
- `MATCH` must be a clause inside `GRAPH_TABLE(...)`. Never write `FROM MATCH ...`.
- Always include a `COLUMNS(...)` clause inside `GRAPH_TABLE(...)`.
- Do not use `PGQL_QUERY()`.
- Keep the query read-only.
- Prefer concise but valid Oracle property graph queries.

## Schema
See [the graph schema summary](../assets/schema_summary.md).

## Oracle edge label syntax
- In Oracle property graph query syntax, do **not** prefix edge labels with a colon.
- Correct: `[SERVED_BY]`
- Wrong: `[:SERVED_BY]`
- Apply the same rule for all edge labels such as `[ORIGINATES_FROM]`, `[LOCATED_ON]`, `[AFFECTED]`, `[CAUSED_BY]`, `[ADDRESSES]`, `[SERVICES]`, `[REFERENCES_OUTAGE]`, and `[REFERENCES_ASSET]`.

## Projection rule
- If the outer `SELECT`, `GROUP BY`, `ORDER BY`, or outer `WHERE` needs a field from the graph match, that field must be returned from `COLUMNS(...)`.
- Do not reference graph properties outside `GRAPH_TABLE(...)` unless they were projected in `COLUMNS(...)`.
- It is valid to use `COUNT(*)` in the outer query and alias it there, for example `COUNT(*) AS outage_count`.

## Filter placement rule
- Prefer graph-property filters inside `GRAPH_TABLE(...)` using its graph query `WHERE` clause.
- Example: `WHERE o.start_time >= ADD_MONTHS(SYSDATE, -6)` belongs inside `GRAPH_TABLE(...)` when `o.start_time` is part of the graph variable logic.

## Validation detail from the app
The backend rejects queries like:
- `FROM MATCH ...`

The backend expects this Oracle style instead:
- `FROM GRAPH_TABLE(<graph_name> MATCH (...) COLUMNS (...))`

## Examples

### Count all vertices
```sql
SELECT COUNT(*) AS vertex_count
FROM GRAPH_TABLE(
  outage_network
  MATCH (v)
  COLUMNS (1 AS dummy)
)
```

### Count all customers
```sql
SELECT COUNT(*) AS customer_count
FROM GRAPH_TABLE(
  outage_network
  MATCH (c IS customer)
  COLUMNS (1 AS dummy)
)
```

### Traverse from substations to circuits
```sql
SELECT substation_name, circuit_name
FROM GRAPH_TABLE(
  outage_network
  MATCH (s IS substation)-[ORIGINATES_FROM]->(c IS circuit)
  COLUMNS (
    s.name AS substation_name,
    c.circuit_name AS circuit_name
  )
)
```

### Find outages connected to root cause assets
```sql
SELECT incident_code, asset_id
FROM GRAPH_TABLE(
  outage_network
  MATCH (o IS outage)-[CAUSED_BY]->(a IS asset)
  COLUMNS (
    o.incident_code AS incident_code,
    a.asset_id AS asset_id
  )
)
```

### Aggregate outages by cause category in the last 6 months
```sql
SELECT cause_category, COUNT(*) AS outage_count
FROM GRAPH_TABLE(
  outage_network
  MATCH (o IS outage)
  WHERE o.start_time >= ADD_MONTHS(SYSDATE, -6)
  COLUMNS (
    o.cause_category AS cause_category
  )
)
GROUP BY cause_category
ORDER BY outage_count DESC, cause_category
FETCH FIRST 50 ROWS ONLY
```
