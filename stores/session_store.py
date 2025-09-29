import os
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from redis.asyncio import Redis
from config.settings import SESSION_TTL_SECONDS


@dataclass
class _RedisState:
    client: Optional[Redis] = None


_state = _RedisState()


def _redis_url() -> str:
    return os.getenv("REDIS_URL")


def get_client() -> Redis:
    client = _state.client
    if client is None:
        client = Redis.from_url(_redis_url(), decode_responses=True)
        _state.client = client
    return client


def _key_for_user(user_id: str) -> str:
    return f"user_session:{user_id}"


def _notify_key(user_id: str, session_id: str) -> str:
    return f"notify_session:{user_id}:{session_id}"


async def get_session_id_for_user(user_id: str) -> Optional[str]:
    r = get_client()
    val = await r.get(_key_for_user(user_id))
    return val if isinstance(val, str) and val else None


async def set_session_id_for_user(user_id: str, session_id: str) -> None:
    r = get_client()
    user_key = _key_for_user(user_id)
    notify_key = _notify_key(user_id, session_id)
    # Set both the session and its paired notify key
    async with r.pipeline(transaction=True) as p:
        p.set(user_key, session_id, ex=SESSION_TTL_SECONDS)
        p.set(notify_key, "1", ex=SESSION_TTL_SECONDS)
        await p.execute()


async def refresh_session_ttl(user_id: str) -> None:
    r = get_client()
    user_key = _key_for_user(user_id)
    session_id = await get_session_id_for_user(user_id)

    if session_id:
        notify_key = _notify_key(user_id, session_id)
        async with r.pipeline(transaction=True) as p:
            p.expire(user_key, SESSION_TTL_SECONDS)
            p.expire(notify_key, SESSION_TTL_SECONDS)
            await p.execute()

        return

    await r.expire(user_key, SESSION_TTL_SECONDS)
