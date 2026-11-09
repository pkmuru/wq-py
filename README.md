# WorkIQ MCP Agent

A small FastAPI service that sits in front of the Microsoft **Work IQ MCP server**.
It lets you list your Copilot agents and ask a question to one of them, all from Swagger UI.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Your Microsoft 365 tenant is enabled for Work IQ
- An Entra ID access token with audience `api://workiq.svc.cloud.microsoft` and scope `WorkIQAgent.Ask`

Getting a token for testing (Azure CLI, after `az login`):

```bash
az account get-access-token --resource api://workiq.svc.cloud.microsoft --query accessToken -o tsv
```

## Setup

```bash
cp .env.example .env     # then paste your token into WORKIQ_ACCESS_TOKEN
uv sync                  # creates .venv and installs dependencies
```

## Run

```bash
uv run fastapi dev app/main.py
```

Open http://127.0.0.1:8000/docs

## Endpoints

| Method | Path                     | Purpose                                   |
|--------|--------------------------|-------------------------------------------|
| GET    | `/health`                | Liveness check                            |
| GET    | `/agents`                | List agents (Work IQ `list_agents` tool)  |
| POST   | `/agents/{agent_id}/ask` | Ask a question (Work IQ `ask` tool)       |

Example body for `/agents/{agent_id}/ask`:

```json
{ "question": "Summarise my unread emails", "conversation_id": null }
```

The answer includes a `conversation_id`. Send it back in the next request to continue the same conversation.

## Project layout

```
app/
  config.py         # settings loaded from .env (pydantic-settings)
  schemas.py        # request/response models (pydantic)
  workiq_client.py  # the only file that talks MCP
  main.py           # FastAPI routes
```

## Errors

| HTTP | Meaning                                                   |
|------|-----------------------------------------------------------|
| 401  | Work IQ rejected the token (expired or missing scope)     |
| 502  | Work IQ returned a tool error (`isError: true`)           |
| 503  | Could not reach the Work IQ server                        |
