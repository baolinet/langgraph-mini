# order_graph.py - 订单处理workflow
from .tools import tools_order, tools_dict
from .state import State
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage

async def call_order_agent(state: State):
    # 1. 直接从 state 获取已解析的用户身份
    user_id = state["user_id"]
    # 2. 查询订单（使用异步调用）
    order = await tools_dict["get_order_by_user_id"].ainvoke({"user_id": user_id})
    # 3. 回复订单状态
    reply = f"您的订单状态：{order['status']}"
    return {"messages": [AIMessage(content=reply)]}

workflow = StateGraph(State)
workflow.add_node("order_agent", call_order_agent)
workflow.add_edge(START, "order_agent")
workflow.add_edge("order_agent", END)
order_graph = workflow.compile()
