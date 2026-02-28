# routers.py - 可扩展路由（可按需添加）
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def index():
    return {"msg": "hello world"}

@router.get("/ping")
def ping():
    return {"msg": "pong"}


@router.get("/health")
async def health():
    return {"status": "healthy", "graph": "agent ready"}