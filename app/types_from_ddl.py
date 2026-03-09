from __future__ import annotations

import re
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .models import GraphEdge, GraphNode


@dataclass(frozen=True)
class TypeRecord:
    type_id: str
    name: str
    display: str
    kind: str  # "VertexType" | "EdgeType"
    properties: list[str]

    def display_name(self) -> str:
        return self.display

    def score(self, query: str) -> float:
        q = query.lower()
        name = self.name.lower()
        display = self.display_name().lower()

        def score_for(value: str) -> float:
            if value == q:
                return 1.0
            if value.startswith(q):
                return 0.9
            if q in value:
                return 0.7
            return 0.0

        return max(score_for(name), score_for(display))

    def preview(self) -> dict:
        return {
            "properties": self.properties[:8],
            "property_count": len(self.properties),
        }


def _split_using_tokens(value: str, tokens: set[str]) -> list[str]:
    remaining = value
    parts: list[str] = []
    while remaining:
        match = None
        for i in range(len(remaining), 1, -1):
            candidate = remaining[:i]
            if candidate in tokens:
                match = candidate
                break
        if match:
            parts.append(match)
            remaining = remaining[len(match) :]
            continue
        chunk = remaining[:3]
        parts.append(chunk)
        remaining = remaining[len(chunk) :]
    return parts


def to_display_name(value: str, tokens: set[str] | None = None) -> str:
    value = value.strip()
    if not value:
        return value
    if "_" not in value and value.isalnum() and any(ch.islower() for ch in value):
        return value
    parts = [p for p in re.split(r"[_\s]+", value) if p]
    if len(parts) == 1 and tokens and value.isupper() and value.isalpha():
        parts = _split_using_tokens(value, tokens)
    if not parts:
        return value
    if len(parts) == 1:
        return parts[0].title()
    first, *rest = parts

    def cap(part: str) -> str:
        if not part:
            return part
        return part[:1].upper() + part[1:].lower()

    first_abbrev = first[:4].lower() if len(first) > 4 else first[:3].lower()
    return cap(first_abbrev) + "".join(cap(p[:3].lower()) for p in rest)


def to_case_name(value: str) -> str:
    """Basic casing for ALL_CAPS identifiers.

    Example: ABC_CDE -> Abc_Cde
    """
    parts = [p for p in re.split(r"[_\s]+", value.strip()) if p]
    return "_".join(p[:1].upper() + p[1:].lower() if p else p for p in parts) if parts else value


def load_display_name_overrides(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    if not path.exists():
        return {}, {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}, {}
    if not isinstance(data, dict):
        return {}, {}
    vertex_overrides = data.get("vertex", {})
    edge_overrides = data.get("edge", {})
    if not isinstance(vertex_overrides, dict):
        vertex_overrides = {}
    if not isinstance(edge_overrides, dict):
        edge_overrides = {}
    return vertex_overrides, edge_overrides


class DdlGraphTypes:
    def __init__(self, *, vertex_types: dict[str, TypeRecord], edge_types: dict[str, TypeRecord], edges: list[GraphEdge]):
        self._vertex_types = vertex_types
        self._edge_types = edge_types
        self._edges = edges

    @classmethod
    def load_default(cls) -> "DdlGraphTypes":
        return _load_default_cached()

    @classmethod
    def from_profile(
        cls,
        *,
        ddl_path: Path,
        display_name_path: Path | None = None,
        friendly_names: str = "short",
    ) -> "DdlGraphTypes":
        return _load_profile_cached(
            str(ddl_path.resolve()),
            str(display_name_path.resolve()) if display_name_path else None,
            str(friendly_names),
        )

    @classmethod
    def from_pg_ddl(
        cls,
        path: Path,
        *,
        display_name_path: Path | None = None,
        friendly_names: str = "short",
    ) -> "DdlGraphTypes":
        text = path.read_text(encoding="utf-8", errors="replace")

        vertex_overrides, edge_overrides = ({}, {})
        # Allow display_name overrides regardless of friendly_names mode.
        # This enables per-graph display control even when the base naming strategy is "raw".
        if display_name_path:
            vertex_overrides, edge_overrides = load_display_name_overrides(display_name_path)

        def display_for(name: str) -> str:
            if friendly_names == "raw":
                return vertex_overrides.get(name, name)
            if friendly_names == "case":
                return to_case_name(name)
            # short
            return vertex_overrides.get(name, to_display_name(name))

        def edge_display_for(label: str, tokens: set[str]) -> str:
            if friendly_names == "raw":
                return edge_overrides.get(label, label)
            if friendly_names == "case":
                return to_case_name(label)
            return edge_overrides.get(label, to_display_name(label, tokens))

        vertex_types: dict[str, TypeRecord] = {}
        edge_types: dict[str, TypeRecord] = {}
        edges: list[GraphEdge] = []

        # Map vertex table identifiers (as used in REFERENCES clauses) to the
        # canonical vertex type id we expose to the UI.
        #
        # Example (outage_pg_dll.sql):
        #   VERTEX TABLES (circuits ... LABEL circuit ...)
        #   EDGE TABLES (... REFERENCES circuits(id) ...)
        # We want edges to connect to v:circuit, not v:circuits.
        table_to_vertex_type_id: dict[str, str] = {}

        # Vertex table blocks supported:
        # 1) Legacy:
        #    "SCHEMA"."TABLE" AS "ALIAS" KEY (...) PROPERTIES (...),
        # 2) Simpler form:
        #    table_name KEY (id) LABEL label_name PROPERTIES (...),

        vertex_legacy_pattern = re.compile(
            r'"(?P<schema>[^"]+)"\."(?P<table>[^"]+)" +AS +"(?P<alias>[^"]+)" +KEY *\([^)]*\) *PROPERTIES *\((?P<props>[^)]*)\) *,',
            re.IGNORECASE | re.MULTILINE,
        )

        vertex_simple_pattern = re.compile(
            r"(?P<table>[A-Z0-9_#$]+) +KEY *\([^)]*\) +LABEL +(?P<label>[A-Z0-9_#$]+) *(?:\r?\n)? *PROPERTIES *\((?P<props>[^)]*)\) *,",
            re.IGNORECASE | re.MULTILINE,
        )

        def _add_vertex(*, name: str, props_raw: str):
            props = [p.strip().strip('"') for p in props_raw.split(",") if p.strip()]
            type_id = f"v:{name}"
            display = display_for(name)
            vertex_types[type_id] = TypeRecord(
                type_id=type_id,
                name=name,
                display=display,
                kind="VertexType",
                properties=props,
            )

        def _register_table_mapping(*, table: str, type_id: str):
            key = table.strip().strip('"')
            if not key:
                return
            # Prefer first seen mapping to keep it deterministic.
            table_to_vertex_type_id.setdefault(key, type_id)

        for m in vertex_legacy_pattern.finditer(text):
            alias = m.group("alias")
            _add_vertex(name=alias, props_raw=m.group("props"))
            _register_table_mapping(table=m.group("table"), type_id=f"v:{alias}")

        for m in vertex_simple_pattern.finditer(text):
            table = m.group("table")
            # prefer LABEL as the type name if present
            name = m.group("label") or table
            _add_vertex(name=name, props_raw=m.group("props"))
            _register_table_mapping(table=table, type_id=f"v:{name}")

        def _resolve_vertex_type_id(ref: str) -> str:
            """Resolve a REFERENCES target (table or alias) to our vertex type id."""
            key = ref.strip().strip('"')
            return table_to_vertex_type_id.get(key, f"v:{key}")

        # Edge table blocks contain LABEL <label> and REFERENCES <vertex alias>.
        # We'll capture:
        #   SOURCE ... REFERENCES <src_alias>
        #   DESTINATION ... REFERENCES <dst_alias>
        #   LABEL <label>
        # Edge blocks supported:
        # 1) Legacy alias form with quoted table and edge alias.
        # 2) Simple form:
        #    table AS edge_alias SOURCE KEY (...) REFERENCES src (id)
        #         DESTINATION KEY (...) REFERENCES dst (id)
        #         LABEL SOME_LABEL
        edge_block_pattern = re.compile(
            r"(?:AS +\"(?P<edge_alias_q>[^\"]+)\"|AS +(?P<edge_alias>[A-Z0-9_#$]+)).*?SOURCE +KEY *\([^)]*\) +REFERENCES +(?P<src>[A-Z0-9_#$\"]+) *\([^)]*\) *(?:\r?\n) *DESTINATION +KEY *\([^)]*\) +REFERENCES +(?P<dst>[A-Z0-9_#$\"]+) *\([^)]*\) *(?:\r?\n) *LABEL +(?P<label>[A-Z0-9_#$]+)",
            re.IGNORECASE | re.DOTALL,
        )

        edge_three_line_pattern = re.compile(
            r"SOURCE +KEY *\([^)]*\) +REFERENCES +(?P<src>[^\s(]+) *\([^)]*\) *(?:\r?\n) *DESTINATION +KEY *\([^)]*\) +REFERENCES +(?P<dst>[^\s(]+) *\([^)]*\) *(?:\r?\n) *LABEL +(?P<label>[^,\s]+)",
            re.IGNORECASE,
        )

        edge_inline_pattern = re.compile(
            r"SOURCE\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<src>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s*(?:\r?\n)\s*DESTINATION\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<dst>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s*(?:\r?\n)\s*LABEL\s+(?P<label>[A-Z0-9_#$]+)",
            re.IGNORECASE | re.DOTALL,
        )

        edge_compact_pattern = re.compile(
            r"SOURCE\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<src>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s+DESTINATION\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<dst>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s+LABEL\s+(?P<label>[A-Z0-9_#$]+)",
            re.IGNORECASE | re.DOTALL,
        )

        edge_any_pattern = re.compile(
            r"SOURCE\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<src>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s+DESTINATION\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<dst>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s+LABEL\s+(?P<label>[A-Z0-9_#$]+)",
            re.IGNORECASE | re.DOTALL,
        )

        edge_one_line_pattern = re.compile(
            r"SOURCE\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<src>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s+DESTINATION\s+KEY\([^)]*\)\s+REFERENCES\s+(?P<dst>[A-Z0-9_#$\"]+)\s*\([^)]*\)\s+LABEL\s+(?P<label>[A-Z0-9_#$]+)",
            re.IGNORECASE,
        )

        edge_seen: set[str] = set()
        # Tokenize based on actual type names (not type_ids like "v:XYZ").
        vertex_tokens = {
            p
            for t in vertex_types.values()
            for p in t.name.split("_")
            if p
        }
        for m in edge_block_pattern.finditer(text):
            src_alias = m.group("src").strip('"')
            dst_alias = m.group("dst").strip('"')
            label = m.group("label")

            display_label = edge_display_for(label, vertex_tokens)

            edge_type_id = f"e:{label}"
            if edge_type_id not in edge_types:
                edge_types[edge_type_id] = TypeRecord(
                    type_id=edge_type_id,
                    name=label,
                    display=display_label,
                    kind="EdgeType",
                    properties=[],
                )

            source_type_id = _resolve_vertex_type_id(src_alias)
            target_type_id = _resolve_vertex_type_id(dst_alias)
            edge_id = f"rel:{source_type_id}:{label}:{target_type_id}"
            if edge_id in edge_seen:
                continue
            edge_seen.add(edge_id)
            edges.append(
                GraphEdge(
                    id=edge_id,
                    source=source_type_id,
                    target=target_type_id,
                    type=label,
                    display_name=display_label,
                    full_name=label,
                    properties={},
                )
            )

        # Fallback: if we didn't capture any edges (common in simpler DDL formats),
        # try matching edge clauses without requiring the initial "AS ...".
        if not edges:
            for m in (
                list(edge_inline_pattern.finditer(text))
                + list(edge_compact_pattern.finditer(text))
                + list(edge_any_pattern.finditer(text))
                + list(edge_one_line_pattern.finditer(text))
                + list(edge_three_line_pattern.finditer(text))
            ):
                src_alias = m.group("src").strip('"')
                dst_alias = m.group("dst").strip('"')
                label = m.group("label")

                display_label = edge_display_for(label, vertex_tokens)

                edge_type_id = f"e:{label}"
                if edge_type_id not in edge_types:
                    edge_types[edge_type_id] = TypeRecord(
                        type_id=edge_type_id,
                        name=label,
                        display=display_label,
                        kind="EdgeType",
                        properties=[],
                    )

                source_type_id = _resolve_vertex_type_id(src_alias)
                target_type_id = _resolve_vertex_type_id(dst_alias)
                edge_id = f"rel:{source_type_id}:{label}:{target_type_id}"
                if edge_id in edge_seen:
                    continue
                edge_seen.add(edge_id)
                edges.append(
                    GraphEdge(
                        id=edge_id,
                        source=source_type_id,
                        target=target_type_id,
                        type=label,
                        display_name=display_label,
                        full_name=label,
                        properties={},
                    )
                )

        return cls(vertex_types=vertex_types, edge_types=edge_types, edges=edges)

    def search(self, query: str, *, limit: int) -> list[TypeRecord]:
        all_types = list(self._vertex_types.values()) + list(self._edge_types.values())
        scored = [(t.score(query), t) for t in all_types]
        scored = [(s, t) for s, t in scored if s > 0]
        scored.sort(key=lambda x: (-x[0], x[1].name))
        return [t for _s, t in scored[:limit]]

    def list_types(self) -> tuple[list[TypeRecord], list[TypeRecord]]:
        vertices = sorted(self._vertex_types.values(), key=lambda t: t.name)
        edges = sorted(self._edge_types.values(), key=lambda t: t.name)
        return vertices, edges

    def get_type(self, type_id: str) -> TypeRecord | None:
        if type_id in self._vertex_types:
            return self._vertex_types[type_id]
        if type_id in self._edge_types:
            return self._edge_types[type_id]
        return None

    def relations_for_types(self, type_ids: set[str]) -> list[GraphEdge]:
        if not type_ids:
            return []
        return [
            e
            for e in self._edges
            if e.source in type_ids and e.target in type_ids
        ]

    def neighborhood(
        self,
        *,
        center_type_id: str,
        edge_labels: set[str] | None,
        direction: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        def edge_ok(e: GraphEdge) -> bool:
            if edge_labels and e.type not in edge_labels:
                return False
            if direction == "in":
                return e.target == center_type_id
            if direction == "out":
                return e.source == center_type_id
            return e.source == center_type_id or e.target == center_type_id

        kept_edges = [e for e in self._edges if edge_ok(e)]

        node_ids = {center_type_id}
        for e in kept_edges:
            node_ids.add(e.source)
            node_ids.add(e.target)

        def node_for(type_id: str) -> GraphNode:
            if type_id in self._vertex_types:
                t = self._vertex_types[type_id]
                return GraphNode(
                    id=t.type_id,
                    label=t.name,
                    display_name=t.display_name(),
                    full_name=t.name,
                    kind=t.kind,
                    properties={"properties": t.properties},
                )
            # If unknown (e.g., DDL parse miss), still return something.
            return GraphNode(id=type_id, label=type_id, kind="VertexType", properties={})

        nodes = [node_for(tid) for tid in sorted(node_ids)]
        return nodes, kept_edges


def extract_property_graph_name(ddl_text: str) -> str | None:
    """Extract CREATE PROPERTY GRAPH <name> from a DDL file.

    Supports quoted names like "SCHEMA"."GRAPH" and unquoted names.
    """

    pattern = re.compile(
        r"CREATE\s+PROPERTY\s+GRAPH\s+(?P<name>(?:\"[^\"]+\"\.)?\"[^\"]+\"|[A-Z0-9_#$]+)",
        re.IGNORECASE,
    )
    match = pattern.search(ddl_text)
    if not match:
        return None
    return match.group("name").strip()


@lru_cache(maxsize=1)
def _load_default_cached() -> "DdlGraphTypes":
    project_root = Path(__file__).resolve().parents[1]
    ddl_path = (project_root / "ddls" / "outage_pg_dll.sql").resolve()
    if not ddl_path.exists():
        alt = (project_root / "ddls" / "outage_pg_dll.sql").resolve()
        if alt.exists():
            ddl_path = alt
    display_names = (project_root / "ew_display_names.json").resolve()
    if not display_names.exists():
        display_names = (project_root / "outage_display_names.json").resolve()
    return DdlGraphTypes.from_pg_ddl(
        ddl_path,
        display_name_path=display_names if display_names.exists() else None,
        friendly_names="short",
    )


@lru_cache(maxsize=16)
def _load_profile_cached(
    ddl_path: str,
    display_name_path: str | None,
    friendly_names: str,
) -> "DdlGraphTypes":
    ddl = Path(ddl_path)
    display = Path(display_name_path) if display_name_path else None
    return DdlGraphTypes.from_pg_ddl(
        ddl,
        display_name_path=display,
        friendly_names=friendly_names,
    )
