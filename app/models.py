from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: str
    label: str
    display_name: str | None = None
    full_name: str | None = None
    kind: str | None = None
    score: float | None = None
    preview: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    results: list[SearchResult]
    limit: int


class GraphNode(BaseModel):
    id: str
    label: str
    display_name: str | None = None
    full_name: str | None = None
    kind: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    display_name: str | None = None
    full_name: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class NeighborhoodResponse(BaseModel):
    center_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    in_limit: int
    out_limit: int
    has_more_in: bool = False
    has_more_out: bool = False


Direction = Literal["in", "out", "both"]
QueryMode = Literal["sql", "pgql"]


class InstanceQueryRequest(BaseModel):
    text: str
    scope: Literal["selected", "all"] = "selected"
    selected_types: list[str] = Field(default_factory=list)
    limit: int | None = None
    execute: bool = False
    sql: str | None = None
    query_mode: QueryMode = "sql"


class InstanceQueryResponse(BaseModel):
    query: str
    scope: str
    columns: list[str]
    rows: list[list[Any]]
    limit: int
    note: str | None = None
    error: str | None = None
