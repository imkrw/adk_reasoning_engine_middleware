from dotenv import load_dotenv
from fastapi import APIRouter
from .index import router as index_router
from .middleware import router as middleware_router


load_dotenv()

api_router = APIRouter()
api_router.include_router(index_router)
api_router.include_router(middleware_router)

__all__ = ["api_router"]
