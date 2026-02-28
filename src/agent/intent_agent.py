# intent_agent.py - 意图识别 Agent（重构版）
from functools import lru_cache
import os

from langchain_core.messages import HumanMessage, BaseMessage

from ..constants import IntentType
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

# 合法的意图值集合（用于严格匹配）
_VALID_INTENTS = {e.value for e in IntentType}


@lru_cache(maxsize=1)
def _get_intent_model():
    """懒加载意图识别模型，从数据库读取配置"""
    # 从数据库获取节点的模型配置
    db = get_db()
    model_record = db.get_node_model_config("main_workflow", "intent_router")

    if not model_record:
        raise ValueError(
            "未找到意图路由器的模型配置。\n"
            "请在数据库中添加该节点的模型配置：\n"
            "  1. 确保 workflow_nodes 表中存在记录 (workflow_name='main_workflow', node_id='intent_router')\n"
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

    cache_key = f"intent_{model_config.model_name}"
    return default_model_factory.create_model(model_config, cache_key)


async def intent_classify(messages: list[BaseMessage]) -> str:
    """
    调用大模型识别用户意图。

    Returns:
        IntentType 枚举值之一：order / logistics / general / unknown
    """
    model = _get_intent_model()
    last_message = messages[-1].content if messages else ""

    valid_values = "/".join(v for v in _VALID_INTENTS if v != IntentType.UNKNOWN)
    prompt = f"""请判断用户问题属于以下哪一类：
- 订单问题（如查询订单、订单状态、取消订单等）：返回 order
- 物流问题（如查询物流、快递信息、物流状态等）：返回 logistics
- 通用对话或任务（如写诗、计算、问答、聊天等）：返回 general
- 无关或无法识别的问题：返回 unknown

只返回其中一个词：{valid_values}，不要返回其他内容。

用户问题：{last_message}"""

    resp = await model.ainvoke([HumanMessage(content=prompt)])
    intent = str(resp.content).strip().lower()

    # 优先：严格枚举值匹配
    if intent in _VALID_INTENTS:
        return intent

    # 兜底：关键词匹配（防御 LLM 输出异常，只匹配英文词）
    if "order" in intent:
        return IntentType.ORDER
    if "logistics" in intent:
        return IntentType.LOGISTICS
    if "general" in intent:
        return IntentType.GENERAL
    return IntentType.UNKNOWN
