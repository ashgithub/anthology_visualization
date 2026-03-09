# Visualization Query Agent Guide

## Purpose
This application can generate two distinct kinds of queries:
- SQL: traditional relational Oracle SQL over relational tables/views
- PGQL: Oracle Property Graph Query Language

## Global rules
- Generate exactly one query and no markdown or commentary.
- The app may ask for SQL or PGQL explicitly; follow that request.
- Use the appropriate skill for the requested mode.
- Do not execute queries yourself. Query execution is handled by the application only when the user clicks Run Query.
- Keep generated queries read-only.

## Skill usage
- Use the `sql-query` skill for relational SQL requests.
- Use the `pgql-query` skill for property graph query requests.

## App behavior
- The backend supplies request-specific context.
- SQL generation and PGQL generation are separate user-facing modes.
- Execution remains outside the agent.
