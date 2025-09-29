import asyncio
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from redis.asyncio.client import PubSub
from stores.session_store import get_client


@dataclass
class _ListenerState:
    task: Optional[asyncio.Task] = None
    pubsub: Optional[PubSub] = None


_state = _ListenerState()


def _reset_state() -> None:
    _state.task = None
    _state.pubsub = None


async def _close_pubsub(ps: PubSub | None) -> None:
    if not ps:
        return
    await ps.close()


def _parse_notify_key(key: str) -> tuple[Optional[str], Optional[str]]:
    # notify_session:<user_id>:<session_id>
    if not key.startswith("notify_session:"):
        return None, None
    parts = key.split(":", 2)
    if len(parts) < 3:
        return None, None
    user_id = parts[1]
    session_id = parts[2]
    return user_id, session_id


async def _listen_expirations() -> None:
    r = get_client()

    await r.config_set("notify-keyspace-events", "Ex")

    ps = r.pubsub()
    _state.pubsub = ps
    await ps.psubscribe("__keyevent@0__:expired")

    try:
        async for msg in ps.listen():
            if msg.get("type") != "pmessage":
                continue

            data = msg.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            if not isinstance(data, str):
                continue

            user_id, session_id = _parse_notify_key(data)
            if user_id and session_id:
                print(f"Session expired: user_id: {user_id}")
    finally:
        await _close_pubsub(ps)
        _reset_state()


async def start_expiry_listener() -> None:
    task = _state.task
    if task and not task.done():
        return
    _state.task = asyncio.create_task(_listen_expirations())


async def stop_expiry_listener() -> None:
    task = _state.task
    if task and not task.done():
        task.cancel()
        await task
    await _close_pubsub(_state.pubsub)
    _reset_state()
