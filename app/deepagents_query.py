from __future__ import annotations

from pathlib import Path
import logging

import httpx
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import wrap_tool_call
from langchain_openai import ChatOpenAI
from oci_openai import OciUserPrincipalAuth
from pydantic import BaseModel, SecretStr

from .db_config import AppConfig

logger = logging.getLogger("visualization")


class GeneratedQuery(BaseModel):
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

    logger.info(
        "DeepAgent model config: model_id=%s endpoint=%s profile=%s compartment=%s",
        oci_config.model_id,
        oci_config.endpoint,
        oci_config.profile,
        oci_config.compartment,
    )

    return ChatOpenAI(
        model=oci_config.model_id,
        api_key=SecretStr("OCI"),
        base_url=oci_config.endpoint,
        http_client=httpx.Client(
            auth=OciUserPrincipalAuth(profile_name=oci_config.profile or "DEFAULT"),
            headers={"CompartmentId": oci_config.compartment},
        ),
    )


@wrap_tool_call
def log_tool_calls(request, handler):
    tool_call = getattr(request, "tool_call", None)
    tool_name = None
    tool_args = None

    if isinstance(tool_call, dict):
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args")

    if tool_name is None:
        tool_name = getattr(request, "name", None) or str(request)
    if tool_args is None:
        tool_args = getattr(request, "args", None)

    logger.info("DeepAgent tool call start: tool=%s args=%s", tool_name, tool_args)
    try:
        result = handler(request)
        logger.info("DeepAgent tool call complete: tool=%s", tool_name)
        return result
    except Exception:
        logger.exception("DeepAgent tool call failed: tool=%s", tool_name)
        raise


def _load_agent_prompt() -> str:
    path = _project_root() / "skills" / "AGENTS.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def generate_query_with_deep_agent(
    config: AppConfig,
    *,
    prompt_context: str,
    question: str,
) -> str:
    model = _build_oci_chat_model(config)
    system_prompt = _load_agent_prompt()
    skills_root = _project_root() / "skills"
    composed_user_prompt = f"{prompt_context}\n\n{question}".strip()

    logger.info("DeepAgent system prompt loaded: %s chars", len(system_prompt))
    logger.info("DeepAgent skills root: %s", skills_root)
    logger.info("DeepAgent prompt_context:\n%s", prompt_context)
    logger.info("DeepAgent question: %s", question)
    logger.info("DeepAgent composed user prompt:\n%s", composed_user_prompt)

    agent = create_deep_agent(
        model=model,
        backend=FilesystemBackend(root_dir=_project_root(), virtual_mode=False),
        response_format=GeneratedQuery,
        system_prompt=system_prompt,
        skills=[str(skills_root)],
        middleware=[log_tool_calls],
    )
    logger.info("DeepAgent created with shared skills directory")

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": composed_user_prompt,
                }
            ]
        }
    )

    logger.info("DeepAgent raw result type: %s", type(result).__name__)
    logger.info("DeepAgent raw result: %s", result)

    structured = result.get("structured_response") if isinstance(result, dict) else None
    if structured is None:
        raise ValueError("Deep Agents result missing structured_response")
    if isinstance(structured, GeneratedQuery):
        final_query = structured.sql.strip()
    else:
        final_query = GeneratedQuery.model_validate(structured).sql.strip()

    logger.info("DeepAgent final generated query:\n%s", final_query)
    return final_query
