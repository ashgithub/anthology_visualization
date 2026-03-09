# Visualization App Guide

## Scope
- This subproject contains the FastAPI service and the browser UI for browsing the **types** of the EW property graph.
- The app is **read-only** and focuses on **schema-level traversal** (vertex types, edge labels, and allowed relationships).

## Tech constraints
- **Backend**: FastAPI (Python).
- **Frontend**: static assets served by FastAPI (no Node backend).
- JS visualization library: **Cytoscape.js** (MVP).

## Conventions
- `visualization/app/`: FastAPI application code.
- `visualization/static/`: static frontend assets (HTML/CSS/JS).
- Keep endpoints parameterized (no raw PGQL execution from the browser).
- For this phase, the backend may parse `ddls/pg_ddl.sql` (or query Oracle metadata) to build the type graph.

## Commands (initial)
- Run dev server:
  - `uv run -m visualization.app.main`
