# logistics_graph.py - 物流处理workflow
from .tools import tools_logistics, tools_dict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
import os
from dotenv import load_dotenv

load_dotenv()

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def call_logistics_agent(state: State):
    # 1. 获取用户身份
    user_name = state["messages"][0].content  # 假设第一个消息是用户名
    user_id = tools_dict["get_user_id"].invoke({"user_name": user_name})
    # 2. 查询订单
    order = tools_dict["get_order_by_user_id"].invoke({"user_id": user_id})
    order_id = order["order_id"]
    # 3. 查询物流
    logistics = tools_dict["get_logistics_by_order_id"].invoke({"order_id": order_id})
    reply = f"您的物流状态：{logistics}"
    return {"messages": [AIMessage(content=reply)]}

workflow = StateGraph(State)
workflow.add_node("logistics_agent", call_logistics_agent)
workflow.add_edge(START, "logistics_agent")
workflow.add_edge("logistics_agent", END)
logistics_graph = workflow.compile()
