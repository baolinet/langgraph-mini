# graph.py - 多workflow主调度
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
from .intent_agent import intent_classify
from .order_graph import order_graph
from .logistics_graph import logistics_graph

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def intent_router(state: State):
    """意图识别agent，调度不同子workflow"""
    intent = await intent_classify(state["messages"])
    if intent == "order":
        # 调用订单workflow
        result = await order_graph.ainvoke(state)
        return {"messages": result["messages"]}
    elif intent == "logistics":
        # 调用物流workflow
        result = await logistics_graph.ainvoke(state)
        return {"messages": result["messages"]}
    else:
        # 无关问题
        return {"messages": [AIMessage(content="对不起，我还不清楚您的问题该如何解决")]} 

workflow = StateGraph(State)
workflow.add_node("intent_router", intent_router)
workflow.add_edge(START, "intent_router")
workflow.add_edge("intent_router", END)
graph = workflow.compile()
