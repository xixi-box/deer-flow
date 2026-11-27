"""Canonical MCP session scope construction."""

from __future__ import annotations

import json
from typing import Any, TypeGuard

THREAD_INCARNATION_CONTEXT_KEY = "thread_incarnation"
THREAD_INCARNATION_METADATA_GUARD_KEY = "__deerflow_thread_incarnation_metadata_guard"
_MISSING = object()

# Prefix that distinguishes a versioned scope from the legacy ``user:thread``
# encoding. Shared with :func:`mcp_scope_belongs_to_thread` so the two can
# never drift apart.
_V2_SCOPE_PREFIX = "v2:"
_CREDENTIAL_SCOPE_PREFIX = "v3:"


def is_valid_thread_incarnation(value: object) -> TypeGuard[str | None]:
    """Return whether *value* is a supported legacy or versioned incarnation."""
    return value is None or (isinstance(value, str) and bool(value))


def mcp_session_scope_key(
    *,
    user_id: str,
    thread_id: str,
    thread_incarnation: str | None = None,
    credential_revision: str | None = None,
) -> str:
    """Return the canonical session key, including the credential revision when supplied.

    A legacy NULL incarnation without caller credentials retains the
    pre-activation scope so rolling upgrades keep existing sessions.
    """
    if not is_valid_thread_incarnation(thread_incarnation):
        raise RuntimeError("MCP session scope requires a non-empty thread incarnation")
    scope = f"{user_id}:{thread_id}"
    if thread_incarnation is None and credential_revision is None:
        return scope
    # A JSON tuple is an unambiguous, versioned encoding even when an opaque
    # user/thread id contains the delimiter used by the legacy scope.
    scope_parts = [user_id, thread_id, thread_incarnation]
    prefix = _V2_SCOPE_PREFIX
    if credential_revision is not None:
        scope_parts.append(credential_revision)
        prefix = _CREDENTIAL_SCOPE_PREFIX
    return prefix + json.dumps(
        scope_parts,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def mcp_scope_belongs_to_thread(scope_key: str, *, user_id: str, thread_id: str) -> bool:
    """Return whether *scope_key* was minted for this user/thread identity.

    Matches the legacy ``user:thread`` scope, the versioned incarnation scope
    and the credential-scoped encoding from :func:`mcp_session_scope_key`.
    Teardown matches every incarnation and credential revision of the user
    and thread (see ``MCPSessionPool.close_thread_scope``).

    The legacy branch is a prefix-free string compare, so a crafted ``user_id``
    containing ``:`` can collide with another owner's legacy key. That can only
    ever over-close (tear down an extra session), never leak one, and the
    versioned encoding — which every incarnation-aware caller uses — is exact.
    """
    if scope_key == f"{user_id}:{thread_id}":
        return True
    if scope_key.startswith(_V2_SCOPE_PREFIX):
        prefix, length = _V2_SCOPE_PREFIX, 3
    elif scope_key.startswith(_CREDENTIAL_SCOPE_PREFIX):
        prefix, length = _CREDENTIAL_SCOPE_PREFIX, 4
    else:
        return False
    try:
        decoded = json.loads(scope_key[len(prefix) :])
    except ValueError:
        return False
    return isinstance(decoded, list) and len(decoded) == length and decoded[0] == user_id and decoded[1] == thread_id


def runtime_thread_incarnation(runtime: Any | None) -> str | None:
    """Read the server-owned incarnation from ``ToolRuntime.context``."""
    if runtime is None:
        # Direct tool invocation has no Agent thread lifecycle and retains the
        # legacy scope. An actual runtime with a missing key remains invalid.
        return None
    context = getattr(runtime, "context", None)
    if not isinstance(context, dict) or THREAD_INCARNATION_CONTEXT_KEY not in context:
        raise RuntimeError("MCP tool execution requires a server-owned thread incarnation")
    value = context[THREAD_INCARNATION_CONTEXT_KEY]
    if not is_valid_thread_incarnation(value):
        raise RuntimeError("MCP tool execution received an invalid thread incarnation")
    if context.get(THREAD_INCARNATION_METADATA_GUARD_KEY) is True:
        config = getattr(runtime, "config", None)
        metadata = config.get("metadata") if isinstance(config, dict) else None
        persisted = metadata.get(THREAD_INCARNATION_CONTEXT_KEY, _MISSING) if isinstance(metadata, dict) else _MISSING
        if persisted is _MISSING:
            if value is not None:
                raise RuntimeError("MCP tool execution received a stale thread incarnation")
        elif not is_valid_thread_incarnation(persisted) or persisted != value:
            raise RuntimeError("MCP tool execution received a stale thread incarnation")
    return value
