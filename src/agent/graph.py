# graph.py - 多workflow主调度（使用YAML配置）
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from .state import State
from .intent_agent import intent_classify
from .order_graph import order_graph
from .logistics_graph import logistics_graph
from .general_graph import general_graph
from .workflow_loader import get_main_workflow_config
import os
from dotenv import load_dotenv

load_dotenv(override=True)

checkpointer = MemorySaver()

config = get_main_workflow_config()
main_model_config = config["nodes"][0]["params"]


async def intent_router(state: State, config: RunnableConfig):
    """意图识别agent，调度不同子workflow"""
    intent = await intent_classify(state["messages"])
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    if intent == "order":
        sub_config = {"configurable": {"thread_id": f"{thread_id}-order"}}
        result = await order_graph.ainvoke({"messages": state["messages"], "user_id": state["user_id"]}, config=sub_config)
        return {"messages": result["messages"]}
    elif intent == "logistics":
        sub_config = {"configurable": {"thread_id": f"{thread_id}-logistics"}}
        result = await logistics_graph.ainvoke({"messages": state["messages"], "user_id": state["user_id"]}, config=sub_config)
        return {"messages": result["messages"]}
    elif intent == "general":
        result = await general_graph.ainvoke({"messages": state["messages"], "user_id": state["user_id"]})
        return {"messages": result["messages"]}
    else:
        default_response = main_model_config.get("default_response", "对不起，我还不清楚您的问题该如何解决")
        return {"messages": [AIMessage(content=default_response)]}

workflow = StateGraph(State)
workflow.add_node("intent_router", intent_router)
workflow.add_edge(START, "intent_router")
workflow.add_edge("intent_router", END)
graph = workflow.compile(checkpointer=checkpointer)
