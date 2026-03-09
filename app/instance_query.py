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


def _build_prompt_context(
    query_mode: QueryMode,
) -> str:
    return (
        "Use your pgql-query skill to generate an Oracle Property Graph Query Language query."
        if query_mode == "pgql"
        else "Use your sql-query skill to generate a traditional relational Oracle SQL query."
    )


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
            prompt_context=_build_prompt_context(query_mode),
            question=text,
        )

    logger.info("Instance query generated raw output:\n%s", generated_query)

    if query_mode == "pgql" and not execute:
        logger.info("Returning PGQL generate-only result")
        return QueryPlan(
            query=generated_query.strip(),
            columns=[],
            rows=[],
            note="PGQL query generated only",
        )

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
