import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routers import api_router
from workers.expiry_listener import start_expiry_listener, stop_expiry_listener


@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
    http_client = httpx.AsyncClient(timeout=timeout)
    app.state.http_client = http_client

    await start_expiry_listener()
    try:
        yield
    finally:
        await stop_expiry_listener()
        try:
            await http_client.aclose()
        except Exception:
            pass


app = FastAPI(
    lifespan=lifespan,
)
app.include_router(api_router)
