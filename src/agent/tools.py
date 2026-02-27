from langchain_core.tools import tool
from typing import Optional
# tools.py - 工具定义

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
