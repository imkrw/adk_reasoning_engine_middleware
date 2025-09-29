from fastapi import APIRouter


router = APIRouter()


@router.get("/")
async def root_index():
    return {"message": "Service is up and running."}
