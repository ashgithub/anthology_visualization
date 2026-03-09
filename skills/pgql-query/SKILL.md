---
name: pgql-query
description: Use this skill when the user asks for Oracle Property Graph Query Language (PGQL) queries.
---

# pgql-query

## Overview
Generate one Oracle Property Graph Query Language query.

## Instructions
1. Treat this skill as the authoritative mode for PGQL.
2. Use [the PGQL reference](references/REFERENCE.md) for rules.
3. Use [the graph schema summary](assets/schema_summary.md) together with graph context supplied by the application.
4. Return exactly one PGQL query and nothing else.
5. Never return Oracle SQL or GRAPH_TABLE syntax in this skill.
