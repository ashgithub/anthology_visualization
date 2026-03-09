from __future__ import annotations

from pathlib import Path
import logging
import traceback

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db_config import load_config, resolve_oracle
from .instance_query import run_instance_query
from .mock_data import clamp_limit, limit_list
from .types_from_ddl import DdlGraphTypes
from .models import (
    Direction,
    GraphNode,
    InstanceQueryRequest,
    InstanceQueryResponse,
    NeighborhoodResponse,
    SearchResponse,
    SearchResult,
)

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = (APP_DIR.parent / "static").resolve()

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50

DEFAULT_IN_LIMIT = 50
DEFAULT_OUT_LIMIT = 50
MAX_NEIGHBOR_LIMIT = 200
DEFAULT_INSTANCE_LIMIT = 50
MAX_INSTANCE_LIMIT = 200
CONFIG_PATH = (APP_DIR.parent / "config" / "db.yaml").resolve()


def _configure_logging() -> None:
    logger = logging.getLogger("visualization")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    has_stream_handler = any(isinstance(h, logging.StreamHandler) for h in logger.handlers)
    if not has_stream_handler:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
        logger.addHandler(handler)




def _load_app_config():
    try:
        return load_config(CONFIG_PATH)
    except ValueError:
        # envyaml strict mode raises ValueError when required $VARS are missing.
        # Let endpoints render a useful error instead of crashing the app.
        logger.exception("Failed to load config")
        return None


def _load_graph_types():
    config = _load_app_config()
    if not config:
        return DdlGraphTypes.load_default()

    profile = config.graphs.get(config.active_graph)
    if not profile:
        return DdlGraphTypes.load_default()

    project_root = APP_DIR.parent.resolve()

    ddl_path = Path(profile.ddl_path)
    if not ddl_path.is_absolute():
        ddl_path = (project_root / ddl_path).resolve()

    display_path = None
    if profile.display_names:
        display_path = Path(profile.display_names)
        if not display_path.is_absolute():
            display_path = (project_root / display_path).resolve()

    return DdlGraphTypes.from_profile(
        ddl_path=ddl_path,
        display_name_path=display_path,
        friendly_names=profile.friendly_names,
    )


_configure_logging()

app = FastAPI(title="EW Graph Visualization")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

logger = logging.getLogger("visualization")


@app.get("/api/config")
def app_config_summary():
    """Expose minimal config info for the UI (which graph profile is active)."""
    config = _load_app_config()
    if not config:
        return {
            "active_graph": "default",
            "ddl_path": "ddls/outage_pg_dll.sql",
            "friendly_names": False,
            "max_artifacts": 25,
            "preload_if_small": True,
        }
    profile = config.graphs.get(config.active_graph)
    return {
        "active_graph": config.active_graph,
        "ddl_path": profile.ddl_path if profile else None,
        "friendly_names": profile.friendly_names if profile else None,
        "max_artifacts": profile.max_artifacts if profile else 25,
        "preload_if_small": profile.preload_if_small if profile else True,
    }


@app.get("/api/overview")
def graph_overview():
    """Return a cheap summary (counts + a suggested small default center).

    Used by the UI to decide whether it can safely auto-load the whole schema graph.
    """

    config = _load_app_config()
    graph_types = _load_graph_types()
    vertex_types, edge_types = graph_types.list_types()
    edges = graph_types.relations_for_types(set(graph_types._vertex_types.keys()))  # type: ignore[attr-defined]

    # Prefer a deterministic "first" vertex type as a reasonable center.
    default_center = vertex_types[0].type_id if vertex_types else None

    max_artifacts = 25
    preload_if_small = True
    if config:
        profile = config.graphs.get(config.active_graph)
        if profile:
            max_artifacts = profile.max_artifacts
            preload_if_small = profile.preload_if_small

    counts = {
        "vertex_types": len(vertex_types),
        "edge_types": len(edge_types),
        "relationships": len(edges),
    }
    counts["artifacts"] = counts["vertex_types"] + counts["relationships"]
    counts["can_view_all"] = counts["artifacts"] <= max_artifacts

    return {
        "counts": counts,
        "default_center": default_center,
        "max_artifacts": max_artifacts,
        "preload_if_small": preload_if_small,
    }


@app.get("/api/view-all", response_model=NeighborhoodResponse)
def view_all():
    """Return the entire type graph if it's small enough.

    Safety: this endpoint enforces the configured max_artifacts to avoid locking up
    the browser on large schemas.
    """

    config = _load_app_config()
    graph_types = _load_graph_types()
    vertex_types, _edge_types = graph_types.list_types()

    # Grab all vertex ids and their relations.
    vertex_ids = set(graph_types._vertex_types.keys())  # type: ignore[attr-defined]
    all_edges = graph_types.relations_for_types(vertex_ids)

    max_artifacts = 25
    if config:
        profile = config.graphs.get(config.active_graph)
        if profile:
            max_artifacts = profile.max_artifacts

    artifacts = len(vertex_ids) + len(all_edges)
    if artifacts > max_artifacts:
        # 400 so UI can show "graph too big" message.
        raise HTTPException(
            status_code=400,
            detail=f"Graph too big to view all: artifacts={artifacts} (limit={max_artifacts}). Use search.",
        )

    # Convert vertex types to GraphNode list. Reuse neighborhood() helper by creating
    # a synthetic center (first vertex) and then overriding nodes/edges.
    center_id = vertex_types[0].type_id if vertex_types else "v:root"
    # Build GraphNode list for all vertices.
    nodes_by_id: dict[str, GraphNode] = {}
    for type_id, t in graph_types._vertex_types.items():  # type: ignore[attr-defined]
        nodes_by_id[type_id] = GraphNode(
            id=t.type_id,
            label=t.name,
            display_name=t.display_name(),
            full_name=t.name,
            kind=t.kind,
            properties={"properties": t.properties},
        )

    return NeighborhoodResponse(
        center_id=center_id,
        nodes=[nodes_by_id[k] for k in sorted(nodes_by_id.keys())],
        edges=all_edges,
        in_limit=0,
        out_limit=0,
        has_more_in=False,
        has_more_out=False,
    )


@app.get("/")
def index():
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path)


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(min_length=1, max_length=200),
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT),
):
    query = q.strip().lower()
    graph_types = _load_graph_types()
    matches = [
        SearchResult(
            id=t.type_id,
            label=t.name,
            display_name=t.display_name(),
            full_name=t.name,
            kind=t.kind,
            score=t.score(query),
            preview=t.preview(),
        )
        for t in graph_types.search(query, limit=limit)
    ]

    results, _has_more = limit_list(matches, limit)
    return SearchResponse(results=results, limit=limit)


@app.get("/api/reference")
def reference():
    graph_types = _load_graph_types()
    vertex_types, edge_types = graph_types.list_types()

    return {
        "vertex_types": [
            {
                "id": t.type_id,
                "name": t.name,
                "display_name": t.display_name(),
                "full_name": t.name,
                "property_count": len(t.properties),
                "properties": t.properties,
            }
            for t in vertex_types
        ],
        "edge_types": [
            {
                "id": t.type_id,
                "name": t.name,
                "display_name": t.display_name(),
                "full_name": t.name,
            }
            for t in edge_types
        ],
    }


@app.get("/api/type/{type_id}", response_model=NeighborhoodResponse)
def type_neighborhood(
    type_id: str,
    direction: Direction = Query(default="both"),
    in_limit: int = Query(DEFAULT_IN_LIMIT, ge=0, le=MAX_NEIGHBOR_LIMIT),
    out_limit: int = Query(DEFAULT_OUT_LIMIT, ge=0, le=MAX_NEIGHBOR_LIMIT),
    edge_types: str | None = Query(
        default=None,
        description="Comma-separated edge types; example: WORKS_AT,PARTNER_WITH",
    ),
):
    graph_types = _load_graph_types()
    edge_type_set = (
        {t.strip() for t in edge_types.split(",") if t.strip()} if edge_types else None
    )

    center_neighbors_nodes, center_neighbors_edges = graph_types.neighborhood(
        center_type_id=type_id,
        edge_labels=edge_type_set,
        direction=direction,
    )

    in_edges = [e for e in center_neighbors_edges if e.target == type_id]
    out_edges = [e for e in center_neighbors_edges if e.source == type_id]

    in_edges_limited, has_more_in = limit_list(
        in_edges,
        clamp_limit(in_limit, default=0, max_value=MAX_NEIGHBOR_LIMIT),
    )
    out_edges_limited, has_more_out = limit_list(
        out_edges,
        clamp_limit(out_limit, default=0, max_value=MAX_NEIGHBOR_LIMIT),
    )

    kept_edge_ids = {e.id for e in (in_edges_limited + out_edges_limited)}
    kept_edges = [e for e in center_neighbors_edges if e.id in kept_edge_ids]
    kept_node_ids = {type_id}
    for e in kept_edges:
        kept_node_ids.add(e.source)
        kept_node_ids.add(e.target)
    node_by_id = {n.id: n for n in center_neighbors_nodes}
    kept_nodes = [node_by_id[nid] for nid in kept_node_ids if nid in node_by_id]

    return NeighborhoodResponse(
        center_id=type_id,
        nodes=kept_nodes,
        edges=kept_edges,
        in_limit=in_limit,
        out_limit=out_limit,
        has_more_in=has_more_in,
        has_more_out=has_more_out,
    )


@app.post("/api/instance-query", response_model=InstanceQueryResponse)
def instance_query(payload: InstanceQueryRequest):
    text = payload.text.strip()
    if not text and not (payload.execute and payload.sql):
        return InstanceQueryResponse(
            query="-- No query generated: empty input",
            scope=payload.scope,
            columns=[],
            rows=[],
            limit=DEFAULT_INSTANCE_LIMIT,
            note="Provide a natural-language request to generate a query.",
        )

    config = _load_app_config()
    if not config:
        # Differentiate "missing file" vs "missing env vars" (strict envyaml).
        cfg_path = str(CONFIG_PATH)
        if CONFIG_PATH.exists():
            return InstanceQueryResponse(
                query="-- Invalid config",
                scope=payload.scope,
                columns=[],
                rows=[],
                limit=DEFAULT_INSTANCE_LIMIT,
                error=(
                    f"Failed to load config at {cfg_path}. "
                    "Likely cause: an environment variable referenced in YAML (e.g. $DB_DSN) is not set."
                ),
                note="Set required env vars (DB_DSN, DB_WALLET_PATH, DB_WALLET_PASS, etc.) or update db.yaml.",
            )
        return InstanceQueryResponse(
            query="-- Missing config",
            scope=payload.scope,
            columns=[],
            rows=[],
            limit=DEFAULT_INSTANCE_LIMIT,
            error=f"Config file not found at {CONFIG_PATH}",
            note="Create config/db.yaml to enable DB queries.",
        )

    try:
        oracle = resolve_oracle(config)
    except ValueError as exc:
        return InstanceQueryResponse(
            query="-- Missing database mapping",
            scope=payload.scope,
            columns=[],
            rows=[],
            limit=config.instance_query.limit_default,
            error=str(exc),
            note="Configure databases.<name> and set graphs.<graph>.db to that name.",
        )

    if not (oracle.user and oracle.password and oracle.dsn):
        return InstanceQueryResponse(
            query="-- Missing credentials",
            scope=payload.scope,
            columns=[],
            rows=[],
            limit=config.instance_query.limit_default,
            error="Oracle credentials are incomplete.",
            note="Fill databases.<db>.username, databases.<db>.password, and databases.<db>.dsn.",
        )

    limit = clamp_limit(
        payload.limit or config.instance_query.limit_default,
        default=config.instance_query.limit_default,
        max_value=config.instance_query.limit_max,
    )
    selected = [s for s in payload.selected_types if s]
    scope = payload.scope
    logger.info(
        "Instance query submitted (mode=%s, execute=%s, scope=%s, selected=%s)",
        payload.query_mode,
        payload.execute,
        scope,
        len(selected),
    )

    try:
        plan = run_instance_query(
            config,
            oracle,
            _load_graph_types(),
            text,
            scope,
            selected,
            limit,
            execute=payload.execute,
            provided_sql=payload.sql,
            query_mode=payload.query_mode,
        )
    except Exception:
        logger.exception("Instance query failed")
        return InstanceQueryResponse(
            query="-- Error generating query",
            scope=scope,
            columns=[],
            rows=[],
            limit=limit,
            error=traceback.format_exc(),
        )

    # If the instance_query layer rejected generated SQL, return it as an error
    # so the UI shows a friendly message and the exact SQL for debugging.
    if plan.note and plan.note.startswith("Rejected generated SQL:"):
        return InstanceQueryResponse(
            query=plan.query,
            scope=scope,
            columns=[],
            rows=[],
            limit=limit,
            error=plan.note,
            note="The model-generated SQL was blocked by server-side validation. Rephrase your request or use the SQL override.",
        )

    scope_note = (
        f"-- Scope: selected types ({', '.join(selected)})"
        if scope == "selected" and selected
        else "-- Scope: full graph"
    )
    logger.info(
        "Instance query results returned (execute=%s, rows=%s)",
        payload.execute,
        len(plan.rows),
    )

    return InstanceQueryResponse(
        query=f"{scope_note}\n{plan.query}",
        scope=scope,
        columns=plan.columns,
        rows=plan.rows,
        limit=limit,
        note=plan.note,
    )


def main():
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
