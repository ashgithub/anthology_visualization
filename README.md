# Visualization (Types Browser)

Standalone FastAPI + static browser UI for browsing the **types** of an Oracle property graph.

## Project layout

- `app/`: FastAPI backend
- `static/`: browser assets
- `config/db.yaml`: graph profile + DB config
- `ddls/`: local copied DDL files used by the app
- `tests/`: extracted visualization tests

## Run (dev)

1. Install dependencies with `uv`:

   - `uv sync`

2. Start the dev server from this project root:

   - `uv run -m app.main`

3. Open:

   - `http://127.0.0.1:8000/`

## API (current)

- `GET /api/search?q=...&limit=10`
- `GET /api/type/{type_id}?direction=both&in_limit=50&out_limit=50&edge_types=...`
- `POST /api/instance-query` (reads `config/db.yaml` for connection info)

## Notes

- This phase is a **types browser**: it reads vertex/edge types from local Property Graph DDL files in `ddls/`.
- Instance queries are wired to OCI GenAI + Oracle DB when a DB config is provided; otherwise they return a helpful error.
- Update `config/db.yaml` before running instance queries.
- `property_exclusions.json` is local to this standalone project.

## Graph profiles (DDL-driven)

The app can be pointed at **one graph at a time** by selecting a graph profile in `config/db.yaml`.

### Example

```yaml
active_graph: ew_demo

graphs:
  ew_demo:
    ddl_path: ddls/ew_pg_ddl.sql
    db: ew_db
    display_names: ew_display_names.json
    friendly_names: true

  outage_demo:
    ddl_path: ddls/outage_pg_dll.sql
    db: outage_db
    display_names: outage_display_names.json
    friendly_names: false
```

## Tests

Run from this project root:

- `uv run pytest`
