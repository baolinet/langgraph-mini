# general_graph.py - 通用任务工作流（重构版）
from functools import lru_cache
import os

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import State
from ..llm import ModelConfig, Provider, Credential, default_model_factory, default_credential_manager
from ..db import get_db


def _get_api_key_from_env(provider: Provider) -> str:
    """从环境变量获取 API Key"""
    env_map = {
        Provider.OPENAI: "OPENAI_API_KEY",
        Provider.ZHIPU: "ZHIPU_API_KEY",
        Provider.MOONSHOT: "MOONSHOT_API_KEY",
        Provider.DEEPSEEK: "DEEPSEEK_API_KEY",
        Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
        Provider.AZURE_OPENAI: "AZURE_OPENAI_API_KEY",
    }

    env_var = env_map.get(provider)
    if not env_var:
        raise ValueError(f"未知的 provider: {provider}")

    api_key = os.getenv(env_var)
    if not api_key:
        raise ValueError(
            f"未设置 {provider.value} 的 API Key 环境变量 ({env_var})。\n"
            f"请设置环境变量或在数据库的 credentials 表中配置真实的 API Key。"
        )

    return api_key


@lru_cache(maxsize=1)
def _get_general_model():
    """懒加载通用任务模型，从数据库读取配置"""
    # 从数据库获取节点的模型配置
    db = get_db()
    model_record = db.get_node_model_config("general_workflow", "general_agent")

    if not model_record:
        raise ValueError(
            "未找到通用任务处理器的模型配置。\n"
            "请在数据库中添加该节点的模型配置：\n"
            "  1. 确保 workflow_nodes 表中存在记录 (workflow_name='general_workflow', node_id='general_agent')\n"
            "  2. 在 node_model_configs 表中为该节点配置模型"
        )

    # 使用数据库中的配置
    provider_name = model_record["provider_name"]
    model_name = model_record["model_name"]
    credential_name = model_record["credential_name"]
    temperature = model_record.get("temperature", 0.7)

    # 创建并注册凭证（如果不存在）
    if not default_credential_manager.get_credential(credential_name):
        # 从数据库获取 API Key，如果是占位符则从环境变量读取
        api_key = model_record.get("api_key")
        if not api_key or api_key.startswith(("sk-xxx", "zhipu-xxx", "kimi-xxx")):
            # 从环境变量读取真实的 API Key
            provider_enum = Provider(provider_name)
            api_key = _get_api_key_from_env(provider_enum)

        credential = Credential(
            provider=Provider(provider_name),
            api_key=api_key,
            base_url=model_record.get("base_url"),
        )
        default_credential_manager.add_credential(credential_name, credential)

    model_config = ModelConfig(
        provider=Provider(provider_name),
        model_name=model_name,
        temperature=temperature,
        credential_name=credential_name,
    )

    cache_key = f"general_{model_config.model_name}"
    return default_model_factory.create_model(model_config, cache_key)


async def general_task_handler(state: State):
    """通用任务处理器，处理非订单/物流的对话任务"""
    resp = await _get_general_model().ainvoke(state["messages"])
    return {"messages": [resp]}


workflow = StateGraph(State)
workflow.add_node("general_agent", general_task_handler)
workflow.add_edge(START, "general_agent")
workflow.add_edge("general_agent", END)
general_graph = workflow.compile(checkpointer=MemorySaver())
