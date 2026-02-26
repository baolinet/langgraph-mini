# order_graph.py - 订单处理workflow
from .tools import tools_order, tools_dict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str

async def call_order_agent(state: State):
    # 1. 直接从 state 获取已解析的用户身份
    user_id = state["user_id"]
    # 2. 查询订单
    order = tools_dict["get_order_by_user_id"].invoke({"user_id": user_id})
    # 3. 回复订单状态
    reply = f"您的订单状态：{order['status']}"
    return {"messages": [AIMessage(content=reply)]}

workflow = StateGraph(State)
workflow.add_node("order_agent", call_order_agent)
workflow.add_edge(START, "order_agent")
workflow.add_edge("order_agent", END)
order_graph = workflow.compile()
