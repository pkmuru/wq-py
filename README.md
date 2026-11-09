# WorkIQ MCP Agent

A small FastAPI service that sits in front of the Microsoft **Work IQ MCP server**.
It lets you list your Copilot agents and ask a question to one of them, all from Swagger UI.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Your Microsoft 365 tenant is enabled for Work IQ
- Either a Work IQ access token (Option 1) or an Entra ID app registration (Option 2), see [Authentication](#authentication)

## Setup

```bash
cp .env.example .env     # then fill in Option 1 or Option 2 (see below)
uv sync                  # creates .venv and installs dependencies
```

## Authentication

The app needs a Work IQ access token (audience `api://workiq.svc.cloud.microsoft`, scope `WorkIQAgent.Ask`).
`app/auth.py` picks one of two options for every request:

| Option | When it is used | What happens |
|--------|-----------------|--------------|
| 1. Fixed token | `WORKIQ_ACCESS_TOKEN` in `.env` is **not empty** | That token is sent to Work IQ. The caller's header is ignored. |
| 2. On-Behalf-Of (OBO) | `WORKIQ_ACCESS_TOKEN` is **empty** | The caller sends `Authorization: Bearer <user token>`. MSAL exchanges it for a Work IQ token for that user. |

### Option 1: fixed token (quick testing)

```bash
az account get-access-token --resource api://workiq.svc.cloud.microsoft --query accessToken -o tsv
```

Paste the result into `WORKIQ_ACCESS_TOKEN` in `.env`.

### Option 2: On-Behalf-Of

1. In Entra ID, create an **app registration** for this API.
2. **Certificates & secrets**: create a client secret.
3. **Expose an API**: set the Application ID URI (`api://<CLIENT_ID>`) and add a scope, e.g. `access_as_user`.
4. **API permissions**: add the delegated permission `WorkIQAgent.Ask` on the Work IQ API and grant admin consent.
5. Fill in `.env`:

   ```env
   WORKIQ_ACCESS_TOKEN=
   TENANT_ID=<directory (tenant) id>
   CLIENT_ID=<application (client) id>
   CLIENT_SECRET=<the secret value>
   SCOPE=api://workiq.svc.cloud.microsoft/WorkIQAgent.Ask
   ```

The caller's token must be issued **for this app** (audience `api://<CLIENT_ID>`), not for Work IQ.
OBO only works when the token is meant for the app that does the exchange.

**Getting a user token for testing:** in *Expose an API → Add a client application*, pre-authorize the
Azure CLI (`04b07795-8ddb-461a-bbee-02f9e1bf7b46`) for your scope. Then run:

```bash
az account get-access-token --scope api://<CLIENT_ID>/access_as_user --query accessToken -o tsv
```

In Swagger UI, click **Authorize** and paste that token.

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
  auth.py           # picks the Work IQ token: fixed token or On-Behalf-Of (MSAL)
  schemas.py        # request/response models (pydantic)
  workiq_client.py  # the only file that talks MCP
  main.py           # FastAPI routes
```

## Errors

| HTTP | Meaning                                                   |
|------|-----------------------------------------------------------|
| 401  | Work IQ rejected the token (expired or missing scope)     |
| 401  | No `Authorization` header sent, or the OBO exchange failed (Option 2) |
| 500  | Option 2 is selected but `TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET` are missing |
| 502  | Work IQ returned a tool error (`isError: true`)           |
| 503  | Could not reach the Work IQ server                        |
