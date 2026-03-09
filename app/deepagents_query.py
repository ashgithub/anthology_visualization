from __future__ import annotations

from pathlib import Path

import httpx
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
from oci_openai import OciUserPrincipalAuth
from pydantic import BaseModel, SecretStr

from .db_config import AppConfig


class GeneratedSql(BaseModel):
    sql: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _build_oci_chat_model(config: AppConfig) -> ChatOpenAI:
    oci_config = config.oci
    if not oci_config:
        raise ValueError("OCI config missing.")
    if not oci_config.endpoint:
        raise ValueError("OCI endpoint missing.")
    if not oci_config.compartment:
        raise ValueError("OCI compartment missing.")
    if not oci_config.model_id:
        raise ValueError("OCI model_id missing.")

    return ChatOpenAI(
        model=oci_config.model_id,
        api_key=SecretStr("OCI"),
        base_url=oci_config.endpoint,
        http_client=httpx.Client(
            auth=OciUserPrincipalAuth(profile_name=oci_config.profile or "DEFAULT"),
            headers={"CompartmentId": oci_config.compartment},
        ),
    )


def generate_sql_with_deep_agent(
    config: AppConfig,
    *,
    system_prompt: str,
    question: str,
) -> str:
    model = _build_oci_chat_model(config)
    agent = create_deep_agent(
        model=model,
        backend=FilesystemBackend(root_dir=_project_root(), virtual_mode=False),
        response_format=GeneratedSql,
        system_prompt=system_prompt,
    )
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        }
    )

    structured = result.get("structured_response") if isinstance(result, dict) else None
    if structured is None:
        raise ValueError("Deep Agents result missing structured_response")
    if isinstance(structured, GeneratedSql):
        return structured.sql.strip()
    return GeneratedSql.model_validate(structured).sql.strip()
