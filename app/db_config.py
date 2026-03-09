from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from envyaml import EnvYAML
import os


@dataclass
class OracleConfig:
    user: str
    password: str
    dsn: str
    wallet_dir: str | None = None
    wallet_password: str | None = None
    schema: str | None = None


@dataclass
class DatabaseConfig:
    """A named database connection configuration.

    Graph profiles can reference one of these by name.
    """

    user: str
    password: str
    dsn: str
    wallet_dir: str | None = None
    wallet_password: str | None = None
    schema: str | None = None


@dataclass
class InstanceQueryConfig:
    limit_default: int = 50
    limit_max: int = 200
    timeout_ms: int = 5000
    max_rows: int = 200


@dataclass
class AppConfig:
    databases: dict[str, DatabaseConfig]
    instance_query: InstanceQueryConfig
    graphs: dict[str, "GraphProfile"]
    active_graph: str
    oci: "OciConfig | None" = None


@dataclass
class GraphProfile:
    """Configuration for a single property graph described by a DDL file."""

    ddl_path: str
    db: str | None = None
    display_names: str | None = None
    # raw | short | case
    friendly_names: str = "short"
    # UI safety: maximum nodes+edges to auto-load for "view all".
    max_artifacts: int = 25
    # If true and total artifacts <= max_artifacts, auto-load full graph on startup.
    preload_if_small: bool = True


def resolve_oracle(config: AppConfig, *, graph: str | None = None) -> OracleConfig:
    """Return the Oracle connection config for the active (or specified) graph.

    The resolved Oracle connection comes from `databases:` and `graphs.<name>.db`.
    """

    if graph is None:
        graph = config.active_graph
    profile = config.graphs.get(graph)
    if not profile or not profile.db:
        raise ValueError(f"Graph profile '{graph}' is missing required 'db' reference")

    db_cfg = config.databases.get(profile.db)
    if not db_cfg:
        raise ValueError(f"Graph profile '{graph}' references unknown database '{profile.db}'")

    return OracleConfig(
        user=db_cfg.user,
        password=db_cfg.password,
        dsn=db_cfg.dsn,
        wallet_dir=db_cfg.wallet_dir,
        wallet_password=db_cfg.wallet_password,
        schema=db_cfg.schema,
    )


@dataclass
class OciConfig:
    config_file: str
    profile: str
    compartment: str
    model_id: str
    endpoint: str


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_config(path: Path) -> AppConfig | None:
    # Important: do NOT override environment variables already set by the process.
    # This allows tests (and deployments) to intentionally unset vars and have
    # envyaml strict mode fail fast.
    load_dotenv(override=False)
    # Ensure envyaml strict-mode cannot be disabled for this application.
    # (The repo-level .env currently sets ENVYAML_STRICT_DISABLE=True, which
    # would otherwise allow unresolved placeholders like "$DB_DSN" to pass
    # through and later fail inside the Oracle driver.)
    os.environ.pop("ENVYAML_STRICT_DISABLE", None)

    # In local dev, db.yaml references env vars like $DB_DSN. If users haven't
    # set them, we still want the app to run in schema-only mode.
    # So: when DB_DSN isn't defined, skip config loading entirely.
    if not os.environ.get("DB_DSN"):
        return None
    if not path.exists():
        return None
    # Force strict mode so unresolved $VARS fail fast.
    # Note: envyaml also supports disabling strictness via ENVYAML_STRICT_DISABLE
    # in the environment; we ignore that for this app because leaking placeholders
    # (e.g. "$DB_DSN") into the Oracle driver produces confusing DPY-4000 errors.
    data = EnvYAML(str(path), strict=True, flatten=False)
    databases_raw = data.get("databases") or {}
    databases: dict[str, DatabaseConfig] = {}
    if isinstance(databases_raw, dict):
        for name, raw in databases_raw.items():
            if not isinstance(raw, dict):
                continue
            user = _as_str(raw.get("username")) or _as_str(raw.get("user")) or ""
            password = _as_str(raw.get("password")) or ""
            dsn = _as_str(raw.get("dsn")) or ""
            if not (user and dsn):
                continue
            databases[str(name)] = DatabaseConfig(
                user=user,
                password=password,
                dsn=dsn,
                wallet_dir=_as_str(raw.get("walletPath") or raw.get("wallet_dir")),
                wallet_password=_as_str(raw.get("walletPass") or raw.get("wallet_password")),
                schema=_as_str(raw.get("tablePrefix") or raw.get("schema")),
            )
    instance_raw = data.get("instance_query") or {}
    instance_query = InstanceQueryConfig(
        limit_default=int(instance_raw.get("limit_default", 50)),
        limit_max=int(instance_raw.get("limit_max", 200)),
        timeout_ms=int(instance_raw.get("timeout_ms", 5000)),
        max_rows=int(instance_raw.get("max_rows", 200)),
    )
    oci_raw = data.get("oci") or {}
    oci_config = None
    if oci_raw:
        oci_config = OciConfig(
            config_file=_as_str(oci_raw.get("configFile")) or "",
            profile=_as_str(oci_raw.get("profile")) or "DEFAULT",
            compartment=_as_str(oci_raw.get("compartment")) or "",
            model_id=_as_str(oci_raw.get("modelId")) or "",
            endpoint=_as_str(oci_raw.get("endpoint")) or "",
        )

    graphs_raw = data.get("graphs") or {}
    graphs: dict[str, GraphProfile] = {}
    if isinstance(graphs_raw, dict):
        for name, raw in graphs_raw.items():
            if not isinstance(raw, dict):
                continue
            ddl_path = _as_str(raw.get("ddl_path") or raw.get("ddlPath"))
            if not ddl_path:
                continue
            db_ref = _as_str(raw.get("db"))
            if not db_ref:
                continue
            display_names = _as_str(raw.get("display_names") or raw.get("displayNames"))
            friendly_names_raw = raw.get("friendly_names", raw.get("friendlyNames", "short"))
            friendly_names = str(friendly_names_raw).strip().lower() if friendly_names_raw is not None else "short"
            if friendly_names in {"true", "1", "yes"}:
                friendly_names = "short"
            if friendly_names in {"false", "0", "no"}:
                friendly_names = "raw"
            if friendly_names not in {"raw", "short", "case"}:
                friendly_names = "short"

            max_artifacts_raw = raw.get("max_artifacts", raw.get("maxArtifacts", 25))
            try:
                max_artifacts = int(max_artifacts_raw)
            except (TypeError, ValueError):
                max_artifacts = 25
            if max_artifacts <= 0:
                max_artifacts = 25

            preload_raw = raw.get("preload_if_small", raw.get("preloadIfSmall", True))
            preload_if_small = True
            if isinstance(preload_raw, str):
                preload_if_small = preload_raw.strip().lower() not in {"false", "0", "no"}
            elif isinstance(preload_raw, bool):
                preload_if_small = preload_raw
            graphs[str(name)] = GraphProfile(
                ddl_path=ddl_path,
                db=db_ref,
                display_names=display_names,
                friendly_names=friendly_names,
                max_artifacts=max_artifacts,
                preload_if_small=preload_if_small,
            )

    active_graph = _as_str(data.get("active_graph") or data.get("activeGraph"))
    if not active_graph:
        active_graph = "default"
    if not graphs:
        graphs = {
            "default": GraphProfile(
                ddl_path="ddls/outage_pg_dll.sql",
                display_names="outage_display_names.json",
                friendly_names="short",
            )
        }
    if active_graph not in graphs:
        # Fall back to first profile deterministically.
        active_graph = sorted(graphs.keys())[0]

    return AppConfig(
        databases=databases,
        instance_query=instance_query,
        graphs=graphs,
        active_graph=active_graph,
        oci=oci_config,
    )
