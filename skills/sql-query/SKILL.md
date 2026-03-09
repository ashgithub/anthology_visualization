---
name: sql-query
description: Use this skill when the user asks for traditional Oracle SQL over relational tables, not property graph query syntax.
---

# sql-query

## Overview
Generate one read-only Oracle SQL query over relational tables and views.

## Instructions
1. Treat this skill as the authoritative mode for relational SQL.
2. Use [the SQL reference](references/REFERENCE.md) for rules.
3. Use [the relational schema summary](assets/schema_summary.md) for tables, columns, and foreign-key relationships.
4. Return exactly one Oracle SQL statement and nothing else.
5. Never use GRAPH_TABLE or PGQL syntax in this skill.
