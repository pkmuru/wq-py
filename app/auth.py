"""Decides which access token we send to Work IQ.

There are two options, checked in this order:

1. WORKIQ_ACCESS_TOKEN is set in .env
   -> use that fixed token for every request (good for quick local testing).

2. WORKIQ_ACCESS_TOKEN is empty
   -> the caller must send their own token in the header
      `Authorization: Bearer <user token>`.
      We exchange it for a Work IQ token with the MSAL "On-Behalf-Of" (OBO) flow,
      so Work IQ sees the request as coming from that user.
"""

import asyncio
from functools import lru_cache

import msal
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

# Reads the "Authorization: Bearer ..." header and adds an "Authorize" button to Swagger UI.
# auto_error=False makes the header optional, because option 1 does not need it.
bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _get_msal_app() -> msal.ConfidentialClientApplication:
    """Create the MSAL client once and reuse it.

    Reusing the same object matters: MSAL keeps an in-memory token cache inside it,
    so a second request with the same user token gets the cached Work IQ token
    instead of calling Entra ID again.
    """
    settings = get_settings()
    return msal.ConfidentialClientApplication(
        client_id=settings.client_id,
        client_credential=settings.client_secret,
        authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
    )


def _exchange_user_token(user_token: str) -> str:
    """Swap the caller's token for a Work IQ token (the On-Behalf-Of flow)."""
    settings = get_settings()

    # MSAL checks the tenant when it is created; a wrong TENANT_ID raises ValueError.
    try:
        msal_app = _get_msal_app()
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"OBO is misconfigured, check TENANT_ID in .env: {exc}",
        ) from exc

    result = msal_app.acquire_token_on_behalf_of(
        user_assertion=user_token,
        scopes=[settings.scope],
    )

    # MSAL does not raise on failure. It returns a dict with either
    # "access_token" (success) or "error" + "error_description" (failure).
    if "access_token" in result:
        return result["access_token"]

    raise HTTPException(
        status_code=401,
        detail=(
            "Could not get a Work IQ token on behalf of the user: "
            f"{result.get('error')}: {result.get('error_description')}"
        ),
    )


async def get_workiq_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency: return the token to send to Work IQ.

    Routes use it like this:  token: str = Depends(get_workiq_token)
    """
    settings = get_settings()

    # Option 1: a fixed token from .env wins.
    if settings.workiq_access_token:
        return settings.workiq_access_token

    # Option 2: On-Behalf-Of. We need the caller's token...
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Send your token in the header: Authorization: Bearer <token>",
        )

    # ...and the app registration details from .env.
    if not (settings.tenant_id and settings.client_id and settings.client_secret):
        raise HTTPException(
            status_code=500,
            detail="OBO is not configured: set TENANT_ID, CLIENT_ID, CLIENT_SECRET in .env",
        )

    # MSAL is synchronous (it blocks while it waits for Entra ID).
    # asyncio.to_thread runs it in a background thread so the server can keep
    # handling other requests in the meantime.
    return await asyncio.to_thread(_exchange_user_token, credentials.credentials)
