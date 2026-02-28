# graph_factory.py - 通用 ReAct Agent Graph 工厂函数（重构版）
from typing import Any, Dict, Optional
import os

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
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


def build_tool_agent_graph(
    workflow_config: Dict[str, Any],
    tools: list,
    use_checkpointer: bool = True,
    model_config: Optional[ModelConfig] = None,
) -> Any:
    """
    通用 ReAct Agent Graph 工厂函数。

    根据 workflow YAML 配置构建带 Tool Calling 的 StateGraph，
    消除 order_graph / logistics_graph 之间的代码重复。

    Args:
        workflow_config: 由 get_*_workflow_config() 返回的 YAML 配置字典
        tools: 该 Agent 可以调用的工具列表
        use_checkpointer: 是否启用 MemorySaver 持久化会话历史
        model_config: 可选的模型配置，如果不提供则从 workflow_config 读取

    Returns:
        已编译的 CompiledStateGraph 实例
    """
    agent_cfg = workflow_config.get("agent", {})
    nodes = workflow_config.get("nodes", [])
    node_cfg = nodes[0] if nodes else {}

    node_id = node_cfg.get("id", "agent")
    system_prompt_template = node_cfg.get("system_prompt", "")

    # 创建模型：优先使用传入的 model_config，否则从数据库配置读取
    if model_config:
        # 使用传入的模型配置（直接实例化）
        cache_key = f"{node_id}_{model_config.model_name}"
        model = default_model_factory.create_model(model_config, cache_key)
    else:
        # 从数据库获取节点的模型配置
        workflow_name = workflow_config.get("name", "unknown")
        db = get_db()
        model_record = db.get_node_model_config(workflow_name, node_id)

        if not model_record:
            raise ValueError(
                f"未找到节点 '{workflow_name}.{node_id}' 的模型配置。\n"
                f"请在数据库中添加该节点的模型配置：\n"
                f"  1. 确保 workflow_nodes 表中存在记录 (workflow_name='{workflow_name}', node_id='{node_id}')\n"
                f"  2. 在 node_model_configs 表中为该节点配置模型"
            )

        # 使用数据库中的配置
        provider_name = model_record["provider_name"]
        model_name = model_record["model_name"]
        credential_name = model_record["credential_name"]
        temperature = agent_cfg.get("temperature") or model_record.get("temperature", 0.7)

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

        cache_key = f"{node_id}_{model_config.model_name}"
        model = default_model_factory.create_model(model_config, cache_key)

    agent = create_react_agent(model, tools)

    async def _agent_node(state: State):
        """通用 Tool Calling Agent 节点"""
        user_id = state.get("user_id", "")
        messages = state["messages"]
        system_msg = system_prompt_template.format(user_id=user_id)
        response = await agent.ainvoke(
            {
                "messages": [
                    {"role": "system", "content": system_msg},
                    *messages,
                ]
            }
        )
        return {"messages": response["messages"]}

    workflow = StateGraph(State)
    workflow.add_node(node_id, _agent_node)
    workflow.add_edge(START, node_id)
    workflow.add_edge(node_id, END)

    checkpointer = MemorySaver() if use_checkpointer else None
    return workflow.compile(checkpointer=checkpointer)
