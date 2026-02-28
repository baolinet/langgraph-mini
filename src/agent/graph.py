# graph.py - 多 workflow 主调度
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from .state import State
from .intent_agent import intent_classify
from .order_graph import order_graph
from .logistics_graph import logistics_graph
from .general_graph import general_graph
from .workflow_loader import get_main_workflow_config, find_node_by_id
from ..constants import IntentType, ErrorMessage

checkpointer = MemorySaver()

_main_config = get_main_workflow_config()
_intent_router_params = find_node_by_id(_main_config, "intent_router").get("params", {})


async def intent_router(state: State, config: RunnableConfig):
    """意图识别节点，根据分类结果调度到对应子 workflow"""
    intent = await intent_classify(state["messages"])
    thread_id = config.get("configurable", {}).get("thread_id", "default")
    sub_input = {"messages": state["messages"], "user_id": state["user_id"]}

    if intent == IntentType.ORDER:
        sub_cfg = {"configurable": {"thread_id": f"{thread_id}-order"}}
        result = await order_graph.ainvoke(sub_input, config=sub_cfg)
        return {"messages": result["messages"]}

    if intent == IntentType.LOGISTICS:
        sub_cfg = {"configurable": {"thread_id": f"{thread_id}-logistics"}}
        result = await logistics_graph.ainvoke(sub_input, config=sub_cfg)
        return {"messages": result["messages"]}

    if intent == IntentType.GENERAL:
        sub_cfg = {"configurable": {"thread_id": f"{thread_id}-general"}}
        result = await general_graph.ainvoke(sub_input, config=sub_cfg)
        return {"messages": result["messages"]}

    # UNKNOWN 或其他未识别意图
    default_response = _intent_router_params.get("default_response", ErrorMessage.UNKNOWN_INTENT)
    return {"messages": [AIMessage(content=default_response)]}


workflow = StateGraph(State)
workflow.add_node("intent_router", intent_router)
workflow.add_edge(START, "intent_router")
workflow.add_edge("intent_router", END)
graph = workflow.compile(checkpointer=checkpointer)
