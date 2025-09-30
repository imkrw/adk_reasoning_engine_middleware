import time
import asyncio
from fastapi import APIRouter, Body, Request
from config.settings import CONTACT_STAFF_MSG
from schemas.payloads import ReceivePayload, OutPayload
from clients.reasoning import create_session, stream_query
from stores.session_store import (
    get_session_id_for_user,
    set_session_id_for_user,
    refresh_session_ttl,
)
from clients.auth import get_access_token
from urllib.parse import urlparse

router = APIRouter()


async def _post_webhook(client, url, body):
    try:
        response = await client.post(url, json=body)
        status = getattr(response, "status_code")
        print(f"Response status: {status}")
    except Exception as e:
        print(f"Error posting to {url}: {repr(e)}")


def _build_base_body(
    payload: ReceivePayload,
    session_id: str,
    session_exists: bool,
    timings: dict[str, float],
) -> dict:
    return {
        "companyId": payload.company_id,
        "userId": payload.user_id,
        "webhook": payload.webhook,
        "sessionId": session_id,
        "sessionExists": session_exists,
        "serviceTimingsUsage": timings,
    }


@router.post("/chat", response_model=OutPayload)
async def middleware_endpoint(
    payload: ReceivePayload = Body(...), request: Request = None
) -> OutPayload:
    service_timings_usage: dict[str, float] = {}

    client = getattr(request.app.state, "http_client")

    # Auth
    t0 = time.perf_counter()
    access_token = await get_access_token()
    auth_headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Authorization": f"Bearer {access_token}",
    }
    service_timings_usage["googleAuth"] = round(time.perf_counter() - t0, 2)

    # Check/refresh session
    t0 = time.perf_counter()
    session_id = await get_session_id_for_user(payload.user_id)
    service_timings_usage["getSessionByUserID"] = round(time.perf_counter() - t0, 2)
    if session_id:
        t0 = time.perf_counter()
        await refresh_session_ttl(payload.user_id)
        service_timings_usage["refreshSessionTTL"] = round(time.perf_counter() - t0, 2)
        session_exists = True
    else:
        t0 = time.perf_counter()
        session_id = await create_session(client, auth_headers, payload.user_id)
        service_timings_usage["createSession"] = round(time.perf_counter() - t0, 2)
        t0 = time.perf_counter()
        await set_session_id_for_user(payload.user_id, session_id)
        service_timings_usage["setSessionByUserID"] = round(time.perf_counter() - t0, 2)
        session_exists = False

    # Stream query
    t0 = time.perf_counter()
    response_text = await stream_query(
        client,
        auth_headers,
        payload.user_id,
        session_id,
        payload.user_message,
    )
    service_timings_usage["streamQuery"] = round(time.perf_counter() - t0, 2)

    contact_human_code = "###CONTACT_STAFF###" in payload.user_message

    hook = payload.webhook.strip()
    notify_hook = payload.webhook_notify.strip() if payload.webhook_notify else None

    base_body = _build_base_body(
        payload, session_id, session_exists, service_timings_usage
    )
    final_message = (
        CONTACT_STAFF_MSG
        if contact_human_code
        else response_text or "No response from engine."
    )
    callback_body = {**base_body, "message": final_message}

    parsed_hook = urlparse(hook)
    if parsed_hook.scheme in ("http", "https") and parsed_hook.netloc:
        asyncio.create_task(_post_webhook(client, hook, callback_body))

    if contact_human_code and notify_hook:
        notify_body = {
            **base_body,
            "webhookNotify": notify_hook,
            "message": CONTACT_STAFF_MSG,
        }
        parsed_notify = urlparse(notify_hook)
        if parsed_notify.scheme in ("http", "https") and parsed_notify.netloc:
            asyncio.create_task(_post_webhook(client, notify_hook, notify_body))

    return OutPayload(
        response_message=response_text or "No response from engine.",
        session_id=session_id,
        session_exists=session_exists,
        service_timings_usage=service_timings_usage,
    )
