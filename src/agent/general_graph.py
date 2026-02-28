# general_graph.py - 通用任务工作流（重构版）
from functools import lru_cache

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import State
from .workflow_loader import get_main_workflow_config
from ..constants import DefaultConfig
from ..llm import create_model_auto


@lru_cache(maxsize=1)
def _get_general_model():
    """懒加载通用任务模型，从 YAML 配置读取参数（使用新的模型管理）"""
    cfg = get_main_workflow_config()
    params = cfg.get("general_task", {}).get("params", {})

    model_name = params.get("model", DefaultConfig.DEFAULT_INTENT_MODEL)
    temperature = params.get("temperature", DefaultConfig.DEFAULT_INTENT_TEMPERATURE)

    return create_model_auto(
        model_name=model_name,
        temperature=temperature,
        credential_name="default"
    )


async def general_task_handler(state: State):
    """通用任务处理器，处理非订单/物流的对话任务"""
    resp = await _get_general_model().ainvoke(state["messages"])
    return {"messages": [resp]}


workflow = StateGraph(State)
workflow.add_node("general_agent", general_task_handler)
workflow.add_edge(START, "general_agent")
workflow.add_edge("general_agent", END)
general_graph = workflow.compile(checkpointer=MemorySaver())
