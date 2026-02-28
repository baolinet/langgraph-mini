# general_graph.py - 通用任务工作流（使用YAML配置）
from .state import State
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from .workflow_loader import get_main_workflow_config
import os
from dotenv import load_dotenv

load_dotenv(override=True)

config = get_main_workflow_config()
general_config = config.get("general_task", {})
model_params = general_config.get("params", {})

model = ChatOpenAI(
    model=model_params.get("model", "kimi-k2-thinking"),
    temperature=model_params.get("temperature", 0.7),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY")
)


async def general_task_handler(state: State):
    """通用任务处理器，处理非订单/物流的对话任务"""
    messages = state["messages"]
    resp = await model.ainvoke(messages)
    return {"messages": [resp]}


workflow = StateGraph(State)
workflow.add_node("general_agent", general_task_handler)
workflow.add_edge(START, "general_agent")
workflow.add_edge("general_agent", END)
general_graph = workflow.compile()
