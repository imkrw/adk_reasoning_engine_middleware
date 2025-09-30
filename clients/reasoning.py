from __future__ import annotations
import json
import httpx
from config.settings import get_query_url, get_stream_url
from fastapi import HTTPException


async def create_session(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    user_id: str,
) -> str:
    payload = {"class_method": "async_create_session", "input": {"user_id": user_id}}
    query_url = get_query_url()
    response = await client.post(query_url, headers=headers, json=payload)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        try:
            detail = response.json()
        except Exception:
            detail = {"text": response.text, "status_code": response.status_code}
        raise HTTPException(
            status_code=502,
            detail={"error": "create_session_failed", "upstream": detail},
        ) from e

    data = response.json()
    session_id = (data or {}).get("output", {}).get("id")
    if not session_id:
        raise HTTPException(
            status_code=502, detail={"error": "create_session_no_id", "upstream": data}
        )
    print(f"Created sessionId: {session_id}")
    return session_id


async def stream_query(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    user_id: str,
    session_id: str,
    message: str,
) -> str:
    payload = {
        "class_method": "async_stream_query",
        "input": {"user_id": user_id, "session_id": session_id, "message": message},
    }

    collected_text: list[str] = []
    stream_url = get_stream_url()
    async with client.stream(
        "POST", stream_url, headers=headers, json=payload, timeout=None
    ) as response:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            try:
                detail = response.json()
            except Exception:
                detail = {"text": response.text, "status_code": response.status_code}
            raise HTTPException(
                status_code=502,
                detail={"error": "stream_query_failed", "upstream": detail},
            ) from e

        # Consume the SSE stream, filter noise, and collect the message chunks.
        # Due to we use LINE application for demo, so streaming is not available.

        async for sp in response.aiter_lines():
            if not sp:
                continue
            if sp.startswith(":"):
                continue
            if sp.lower() in ("[done]", "event: end"):
                continue
            if sp.startswith("data:"):
                sp = sp[len("data:") :].strip()

            sp = sp.strip()
            if not sp:
                continue

            try:
                parsed_message = json.loads(sp)
            except json.JSONDecodeError:
                continue

            if not isinstance(parsed_message, dict):
                continue

            content = parsed_message.get("content")
            if not isinstance(content, dict):
                continue

            parts = content.get("parts")
            if not isinstance(parts, list):
                continue

            for part in parts:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text:
                    collected_text.append(text)

    return "".join(collected_text).strip()
