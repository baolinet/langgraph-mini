# graph.py - 多workflow主调度
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from .state import State
from .intent_agent import intent_classify
from .order_graph import order_graph
from .logistics_graph import logistics_graph
import os
from dotenv import load_dotenv

load_dotenv(override=True)


async def general_task_handler(state: State):
    """通用任务处理器，处理非订单/物流的对话任务"""
    model = ChatOpenAI(
        model="kimi-k2-thinking",
        temperature=0.7,
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    messages = state["messages"]
    resp = await model.ainvoke(messages)
    return {"messages": [resp]}


async def intent_router(state: State):
    """意图识别agent，调度不同子workflow"""
    intent = await intent_classify(state["messages"])
    if intent == "order":
        result = await order_graph.ainvoke({"messages": state["messages"], "user_id": state["user_id"]})
        return {"messages": result["messages"]}
    elif intent == "logistics":
        result = await logistics_graph.ainvoke({"messages": state["messages"], "user_id": state["user_id"]})
        return {"messages": result["messages"]}
    elif intent == "general":
        result = await general_task_handler(state)
        return {"messages": result["messages"]}
    else:
        return {"messages": [AIMessage(content="对不起，我还不清楚您的问题该如何解决")]}

workflow = StateGraph(State)
workflow.add_node("intent_router", intent_router)
workflow.add_edge(START, "intent_router")
workflow.add_edge("intent_router", END)
graph = workflow.compile()
