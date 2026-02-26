from langchain_core.tools import tool
from typing import Optional
# tools.py - 工具定义

# 模拟 token -> 用户信息映射表（实际应查 Redis/DB 中的 session）
_TOKEN_USER_MAP = {
    "token-alice": {"user_id": "user-001", "user_name": "Alice"},
    "token-bob":   {"user_id": "user-002", "user_name": "Bob"},
}

def resolve_user_by_token(access_token: Optional[str]) -> Optional[dict]:
    """根据 access_token 解析用户身份，返回 {user_id, user_name}，无效则返回 None"""
    if not access_token:
        return None
    return _TOKEN_USER_MAP.get(access_token)

@tool
def get_user_id(user_name: str) -> str:
    """根据用户名查询用户ID（模拟）"""
    # 实际应查数据库，这里模拟
    return "user-123"

@tool
def get_order_by_user_id(user_id: str) -> dict:
    """根据用户ID查询订单信息（模拟）"""
    # 实际应查数据库，这里模拟
    return {"order_id": "order-456", "status": "已发货"}

@tool
def get_logistics_by_order_id(order_id: str) -> str:
    """根据订单号查询物流状态（模拟）"""
    # 实际应查物流系统，这里模拟
    return "快递已到达配送站，预计明天送达"

tools_order = [get_user_id, get_order_by_user_id]
tools_logistics = [get_user_id, get_order_by_user_id, get_logistics_by_order_id]

# 工具字典（便于graph.py调用）
tools_dict = {
    "get_user_id": get_user_id,
    "get_order_by_user_id": get_order_by_user_id,
    "get_logistics_by_order_id": get_logistics_by_order_id
}
