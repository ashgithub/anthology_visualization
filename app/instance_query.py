from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any
import logging

import oracledb

from .db_config import AppConfig, OracleConfig
from .deepagents_query import generate_query_with_deep_agent
from .models import QueryMode
from .types_from_ddl import DdlGraphTypes, extract_property_graph_name

logger = logging.getLogger("visualization")


@dataclass
class QueryPlan:
    query: str
    columns: list[str]
    rows: list[list[Any]]
    note: str | None = None


def _extract_graph_name(config: AppConfig) -> str | None:
    """Best-effort extraction of the property graph name from the active DDL file."""

    profile = config.graphs.get(config.active_graph)
    if not profile:
        return None
    ddl_path = Path(profile.ddl_path)
    project_root = Path(__file__).resolve().parents[1]
    if not ddl_path.is_absolute():
        ddl_path = (project_root / ddl_path).resolve()
    if not ddl_path.exists():
        return None
    ddl_text = ddl_path.read_text(encoding="utf-8", errors="replace")
    return extract_property_graph_name(ddl_text)


def _build_schema_summary(graph: DdlGraphTypes, max_types: int = 80) -> str:
    vertex_types, edge_types = graph.list_types()

    vertex_lines = [f"- {t.name}" for t in vertex_types[:max_types]]
    edge_lines = [f"- {e.name}" for e in edge_types[:max_types]]

    summary_lines = [
        f"Vertex types ({len(vertex_types)} total, showing {len(vertex_lines)}):",
        *vertex_lines,
        f"Edge types ({len(edge_types)} total, showing {len(edge_lines)}):",
        *edge_lines,
        "Note: Use the property graph defined by the active DDL profile.",
    ]
    return "\n".join(summary_lines)


def _load_property_exclusions() -> dict[str, list[str]]:
    path = (Path(__file__).resolve().parents[1] / "property_exclusions.json").resolve()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    vertex = data.get("vertex", {})
    if not isinstance(vertex, dict):
        return {}
    default_exclusions = vertex.get("DEFAULT", [])
    if not isinstance(default_exclusions, list):
        default_exclusions = []
    return {
        "vertex_default": [str(p) for p in default_exclusions if p],
    }


def _filter_properties(props: list[str], exclusions: dict[str, list[str]], max_props: int) -> list[str]:
    exclude = {p.upper() for p in exclusions.get("vertex_default", [])}
    filtered = [p for p in props if p.upper() not in exclude]
    return filtered[:max_props]


def _build_rich_summary(graph: DdlGraphTypes, selected_types: list[str], max_props: int = 12) -> str:
    exclusions = _load_property_exclusions()
    type_ids = {f"v:{t}" if not t.startswith("v:") else t for t in selected_types}
    nodes = [graph.get_type(tid) for tid in type_ids]
    nodes = [n for n in nodes if n and n.kind == "VertexType"]
    edges = graph.relations_for_types(type_ids)

    if not nodes:
        return "Selected scope has no vertex types to summarize."

    lines = ["Selected types (rich summary):"]
    for n in nodes:
        props = _filter_properties(list(n.properties), exclusions, max_props)
        props_text = ", ".join(props) if props else "(no properties listed)"
        lines.append(f"- {n.name}: {props_text}")

    if edges:
        lines.append("Relationships:")
        for e in edges[:80]:
            src = e.source.removeprefix("v:")
            dst = e.target.removeprefix("v:")
            lines.append(f"- {e.type}: {src} -> {dst}")
    return "\n".join(lines)


def _build_prompt_context(
    config: AppConfig,
    graph: DdlGraphTypes,
    scope: str,
    selected_types: list[str],
    query_mode: QueryMode,
) -> str:
    graph_name = _extract_graph_name(config)

    if scope == "selected" and selected_types:
        schema_summary = _build_rich_summary(graph, selected_types)
    else:
        schema_summary = _build_schema_summary(graph)

    mode_hint = (
        "Use your pgql-query skill to generate an Oracle Property Graph Query Language query."
        if query_mode == "pgql"
        else "Use your sql-query skill to generate a traditional relational Oracle SQL query."
    )
    graph_hint = f"Active property graph name: {graph_name}" if graph_name else "Active property graph name: (unknown)"
    return "\n".join([mode_hint, graph_hint, schema_summary])


def _connect_db(oracle: OracleConfig) -> oracledb.Connection:
    return oracledb.connect(
        user=oracle.user,
        password=oracle.password,
        dsn=oracle.dsn,
        config_dir=oracle.wallet_dir,
        wallet_location=oracle.wallet_dir,
        wallet_password=oracle.wallet_password,
    )


def _execute_query(conn: oracledb.Connection, sql: str):
    with conn.cursor() as cur:
        cur.execute(sql)
        return [d[0] for d in cur.description], cur.fetchmany(200)


_BAD_SQL_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bPGQL_QUERY\b", re.IGNORECASE), "Do not use PGQL_QUERY(); use GRAPH_TABLE(<graph> MATCH ... COLUMNS ...)"),
    (re.compile(r"\bFROM\s+MATCH\b", re.IGNORECASE), "MATCH must be a clause inside GRAPH_TABLE; do not write 'FROM MATCH ...'."),
]


def _validate_generated_sql(sql: str) -> str | None:
    for pattern, msg in _BAD_SQL_HINTS:
        if pattern.search(sql):
            return msg
    lowered = sql.lower()
    mentions_graph = any(tok in lowered for tok in ["graph_table", "property graph", "match", "pgql"])
    if mentions_graph:
        if "graph_table" not in lowered:
            return "Graph queries must use GRAPH_TABLE(...) syntax."
        if " match " not in lowered and "\nmatch" not in lowered and "\tmatch" not in lowered:
            return "Graph queries must include a MATCH clause inside GRAPH_TABLE."
        if "columns" not in lowered:
            return "Graph queries must include a COLUMNS(...) clause inside GRAPH_TABLE."
    return None


def _has_row_limit(sql: str) -> bool:
    lowered = sql.lower()
    return "fetch first" in lowered or "offset" in lowered or "rownum" in lowered


def run_instance_query(
    config: AppConfig,
    oracle: OracleConfig,
    graph: DdlGraphTypes,
    text: str,
    scope: str,
    selected_types: list[str],
    limit: int,
    *,
    execute: bool = False,
    provided_sql: str | None = None,
    query_mode: QueryMode = "sql",
) -> QueryPlan:
    logger.info(
        "Instance query start: mode=%s execute=%s scope=%s selected_types=%s text=%s",
        query_mode,
        execute,
        scope,
        selected_types,
        text,
    )
    if provided_sql:
        logger.info("Instance query using provided query override")
        generated_query = provided_sql
    else:
        generated_query = generate_query_with_deep_agent(
            config,
            prompt_context=_build_prompt_context(config, graph, scope, selected_types, query_mode),
            question=text,
        )

    logger.info("Instance query generated raw output:\n%s", generated_query)

    if query_mode == "pgql":
        logger.info("Returning PGQL generate-only result")
        return QueryPlan(
            query=generated_query.strip(),
            columns=[],
            rows=[],
            note="PGQL generated only; execution is not enabled for PGQL mode yet",
        )

    extra_filters = ""
    if scope == "selected" and selected_types:
        joined = ", ".join(f"'{t}'" for t in selected_types[:25])
        extra_filters = f"vertex_type IN ({joined})"

    sql = generated_query.strip()
    if sql.startswith("```"):
        sql = re.sub(r"^```[a-zA-Z0-9_]*\n?", "", sql)
        sql = re.sub(r"\n?```$", "", sql)
        sql = sql.strip()

    sql = sql.rstrip("; ")

    logger.info("SQL after fence stripping / trim:\n%s", sql)
    validation_error = _validate_generated_sql(sql)
    if validation_error:
        return QueryPlan(
            query=sql,
            columns=[],
            rows=[],
            note=f"Rejected generated SQL: {validation_error}",
        )
    if extra_filters:
        if " where " in sql.lower():
            sql += f" AND {extra_filters}"
        else:
            sql += f" WHERE {extra_filters}"
    if not _has_row_limit(sql):
        sql += f" FETCH FIRST {limit} ROWS ONLY"

    if not execute:
        logger.info("Returning SQL generate-only result")
        return QueryPlan(query=sql, columns=[], rows=[], note="Query generated only")

    logger.info("Executing SQL against Oracle")
    conn = _connect_db(oracle)
    try:
        cols, rows = _execute_query(conn, sql)
    finally:
        conn.close()

    return QueryPlan(query=sql, columns=cols, rows=rows)
