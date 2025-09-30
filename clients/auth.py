from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from google.auth import default as google_auth_default
from google.auth.credentials import Credentials, TokenState
from google.auth.transport.requests import Request as GoogleAuthRequest


@dataclass
class _AuthState:
    credentials: Optional[Credentials] = None
    auth_request: Optional[GoogleAuthRequest] = None
    refresh_lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_state = _AuthState()


def _initialize_state() -> tuple[Credentials, GoogleAuthRequest]:
    current_credentials, _ = google_auth_default()
    auth_request = GoogleAuthRequest()
    _state.credentials = current_credentials
    _state.auth_request = auth_request
    return current_credentials, auth_request


async def get_access_token() -> str:
    current_credentials = _state.credentials
    auth_request = _state.auth_request

    if current_credentials is None or auth_request is None:
        current_credentials, auth_request = _initialize_state()

    token_state = current_credentials.token_state
    token = current_credentials.token
    if token_state is TokenState.FRESH and token:
        return token

    # Refresh only once across tasks; run blocking work off the event loop.
    async with _state.refresh_lock:
        current_credentials = _state.credentials
        auth_request = _state.auth_request
        if current_credentials is None or auth_request is None:
            current_credentials, auth_request = _initialize_state()

        if (
            current_credentials.token_state is not TokenState.FRESH
            or not current_credentials.token
        ):
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, current_credentials.refresh, auth_request)

    current_credentials = _state.credentials
    token = current_credentials.token if current_credentials else None
    if not token:
        raise RuntimeError("Failed to acquire Google access token")
    return token
