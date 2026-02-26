# routers.py - 可扩展路由（可按需添加）
from fastapi import APIRouter

router = APIRouter()

@router.get("/ping")
def ping():
    return {"msg": "pong"}
