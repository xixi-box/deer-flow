"""Request-scoped credentials for deployment stdio MCP connections."""

from __future__ import annotations

import asyncio
import hmac
import json
import os
import secrets
import subprocess
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, TextIO, cast

from langchain_core.tools import ToolException
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from deerflow.config.extensions_config import ExtensionsConfig, McpServerConfig
from deerflow.runtime.secret_context import extract_request_secrets
from deerflow.runtime.user_context import get_authenticated_user_id, resolve_runtime_user_id

_revision_key = secrets.token_bytes(32)


def resolve_stdio_credentials(server_name: str, owner: str, mapping: Mapping[str, str], context: Any) -> dict[str, str]:
    supplied = extract_request_secrets(context)
    environment = {}
    for name, field_name in mapping.items():
        value = supplied.get(field_name, "")
        if not value.strip() or "\x00" in value:
            raise ToolException(f"MCP server '{server_name}' requires a valid credential field '{field_name}' for account '{owner}'. Supply it in config.context.secrets.")
        environment[name] = value
    return environment


def credential_revision(environment: dict[str, str]) -> str:
    canonical = json.dumps(environment, sort_keys=True).encode()
    return hmac.digest(_revision_key, canonical, "sha256").hex()


@dataclass(frozen=True, slots=True)
class StdioCredentialBinding:
    server_name: str
    server: McpServerConfig = field(repr=False)
    owner: str
    revision: str = field(repr=False)

    async def resolve_for_call(self, runtime: Any) -> dict[str, str]:
        if get_authenticated_user_id() != self.owner or resolve_runtime_user_id(runtime) != self.owner:
            raise ToolException("These MCP tools belong to another user")
        try:
            current = await asyncio.to_thread(ExtensionsConfig.from_file)
        except Exception:
            raise ToolException("MCP credential policy is unavailable") from None
        if current.mcp_servers.get(self.server_name) != self.server:
            raise ToolException(f"MCP server '{self.server_name}' changed. Start a new run to reload its tools.")
        environment = resolve_stdio_credentials(self.server_name, self.owner, self.server.env_from_context or {}, getattr(runtime, "context", None))
        if credential_revision(environment) != self.revision:
            raise ToolException(f"Credentials for MCP server '{self.server_name}' changed. Start a new run to reload its tools.")
        return environment


def merge_stdio_credentials(static_env: Mapping[str, str], credentials: Mapping[str, str]) -> dict[str, str]:
    if os.name != "nt":
        return {**static_env, **credentials}
    # Windows folds environment names, so remove aliases before merging.
    targets = {name.upper() for name in credentials}
    return {**{name: value for name, value in static_env.items() if name.upper() not in targets}, **credentials}


@asynccontextmanager
async def create_credentialed_stdio_session(connection: dict[str, Any]) -> AsyncIterator[ClientSession]:
    # The adapter expands ${VAR} references and logs some failure values.
    # Request secrets must pass to the SDK literally, with child stderr kept
    # out of the shared Gateway log.
    server = StdioServerParameters(command=connection["command"], args=connection["args"], cwd=connection.get("cwd"), env=connection["env"])
    async with stdio_client(server, errlog=cast(TextIO, subprocess.DEVNULL)) as (read, write), ClientSession(read, write) as session:
        yield session
