"""Thin client for the Microsoft Work IQ MCP server.

This is the only module that knows about MCP. The rest of the app just calls
`list_agents()` and `ask()`.
"""

import json
from typing import Any

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client
from mcp.shared.exceptions import MCPError
from mcp_types import TextContent

from app.config import get_settings
from app.schemas import Agent, AskResponse


class WorkIQError(Exception):
    """Raised when the Work IQ call fails. `status_code` is the HTTP status we should return."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


async def _call_tool(token: str, name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Open a connection, call one tool, and return its parsed JSON result.

    `token` is the Work IQ access token (see app/auth.py for where it comes from).
    """
    settings = get_settings()

    # The MCP SDK hides HTTP status codes, so remember the last one ourselves.
    last_status: dict[str, int] = {}

    async def remember_status(response: httpx2.Response) -> None:
        last_status["code"] = response.status_code

    http_client = create_mcp_http_client(
        headers={"Authorization": f"Bearer {token}"}
    )
    http_client.event_hooks["response"] = [remember_status]
    transport = streamable_http_client(settings.workiq_mcp_url, http_client=http_client)

    try:
        async with http_client, Client(transport, mode="legacy") as client:
            result = await client.call_tool(name, arguments or {})
    except Exception as exc:
        raise _to_workiq_error(exc, last_status.get("code")) from exc

    # Work IQ returns its payload as JSON text inside the first TextContent block.
    text = "\n".join(c.text for c in result.content if isinstance(c, TextContent))

    if result.is_error:
        raise WorkIQError(text or f"Tool '{name}' returned an error")

    if not text:
        return result.structured_content

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _to_workiq_error(exc: Exception, http_status: int | None) -> WorkIQError:
    """Turn whatever the MCP SDK raised into one clear WorkIQError."""
    if http_status in (401, 403):
        return WorkIQError(
            "Work IQ rejected the token (expired or missing WorkIQAgent.Ask scope).",
            status_code=401,
        )

    # The SDK wraps errors in ExceptionGroups; find the first real exception inside.
    root = exc
    while isinstance(root, BaseExceptionGroup) and root.exceptions:
        root = root.exceptions[0]

    if isinstance(root, MCPError):
        suffix = f" (HTTP {http_status})" if http_status else ""
        return WorkIQError(f"Work IQ error: {root.message}{suffix}", status_code=502)

    if isinstance(root, (httpx2.HTTPError, OSError)):
        return WorkIQError(f"Could not reach Work IQ: {root}", status_code=503)

    return WorkIQError(f"Unexpected error: {root!r}", status_code=502)


async def list_agents(token: str) -> list[Agent]:
    """Return the agents available to the signed-in user."""
    data = await _call_tool(token, "list_agents")
    return [Agent.model_validate(item) for item in data]


async def ask(
    token: str, question: str, agent_id: str, conversation_id: str | None = None
) -> AskResponse:
    """Ask a question to a specific agent."""
    arguments: dict[str, Any] = {"question": question, "agentId": agent_id}
    if conversation_id:
        arguments["conversationId"] = conversation_id

    data = await _call_tool(token, "ask", arguments)

    # Normal case: {"response": "...", "conversationId": "..."}.
    if isinstance(data, dict):
        return AskResponse(
            agent_id=agent_id,
            response=str(data.get("response", "")),
            conversation_id=data.get("conversationId"),
        )

    # Fallback if the server returns plain text.
    return AskResponse(agent_id=agent_id, response=str(data), conversation_id=None)
