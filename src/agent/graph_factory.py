# graph_factory.py - 通用 ReAct Agent Graph 工厂函数（重构版）
from typing import Any, Dict, Optional

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from .state import State
from ..llm import ModelConfig, create_model_from_yaml, Provider


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

    # 创建模型
    if model_config:
        # 使用传入的模型配置
        from ..llm import default_model_factory
        cache_key = f"{node_id}_{model_config.model_name}"
        model = default_model_factory.create_model(model_config, cache_key)
    else:
        # 从 YAML 配置创建模型（兼容旧配置）
        cache_key = f"{node_id}_{agent_cfg.get('model', 'default')}"
        model = create_model_from_yaml(agent_cfg, provider=Provider.CUSTOM, cache_key=cache_key)

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
