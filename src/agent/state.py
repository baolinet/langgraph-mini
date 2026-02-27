# state.py - 共享状态类型定义
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict, Annotated


class State(TypedDict):
    """所有 Graph 共用的状态类型"""
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
