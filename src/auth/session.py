# auth/session.py - 会话管理工具
"""
会话管理工具模块

注意：当前项目使用 LangGraph 的 checkpointer 来管理会话状态，
本模块仅提供辅助工具函数。如需完整的会话管理功能，可使用 LangGraph 内置的持久化方案。
"""
from datetime import datetime


def create_session_token(user_id: str) -> str:
    """
    创建新的 session token

    Args:
        user_id: 用户ID

    Returns:
        格式为 "session_{user_id}_{timestamp}" 的会话令牌
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    return f"session_{user_id}_{timestamp}"
