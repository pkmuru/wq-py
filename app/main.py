"""FastAPI entry point. Run with:  uv run fastapi dev app/main.py"""

from fastapi import Depends, FastAPI, HTTPException

from app import workiq_client
from app.auth import get_workiq_token
from app.schemas import Agent, AskRequest, AskResponse
from app.workiq_client import WorkIQError

app = FastAPI(
    title="WorkIQ MCP Agent",
    description="Middle layer that calls the Microsoft Work IQ MCP server.",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness check. Does not contact Work IQ."""
    return {"status": "ok"}


@app.get("/agents", response_model=list[Agent], tags=["agents"])
async def get_agents(token: str = Depends(get_workiq_token)) -> list[Agent]:
    """List the agents available to the signed-in user."""
    try:
        return await workiq_client.list_agents(token)
    except WorkIQError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@app.post("/agents/{agent_id}/ask", response_model=AskResponse, tags=["agents"])
async def ask_agent(
    agent_id: str, body: AskRequest, token: str = Depends(get_workiq_token)
) -> AskResponse:
    """Ask a question to one agent. Use `conversation_id` to continue a chat."""
    try:
        return await workiq_client.ask(token, body.question, agent_id, body.conversation_id)
    except WorkIQError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
