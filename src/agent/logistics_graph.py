# logistics_graph.py - 物流处理workflow
from .tools import tools_logistics, tools_dict
from .state import State
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage

async def call_logistics_agent(state: State):
    # 1. 直接从 state 获取已解析的用户身份
    user_id = state["user_id"]
    # 2. 查询订单（使用异步调用）
    order = await tools_dict["get_order_by_user_id"].ainvoke({"user_id": user_id})
    order_id = order["order_id"]
    # 3. 查询物流（使用异步调用）
    logistics = await tools_dict["get_logistics_by_order_id"].ainvoke({"order_id": order_id})
    reply = f"您的物流状态：{logistics}"
    return {"messages": [AIMessage(content=reply)]}

workflow = StateGraph(State)
workflow.add_node("logistics_agent", call_logistics_agent)
workflow.add_edge(START, "logistics_agent")
workflow.add_edge("logistics_agent", END)
logistics_graph = workflow.compile()
