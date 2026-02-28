# intent_agent.py - 意图识别 Agent（重构版）
from typing import Optional
from functools import lru_cache

from langchain_core.messages import HumanMessage, BaseMessage

from ..constants import IntentType, DefaultConfig
from ..llm import create_model_auto
from .workflow_loader import get_main_workflow_config, find_node_by_id

# 合法的意图值集合（用于严格匹配）
_VALID_INTENTS = {e.value for e in IntentType}


@lru_cache(maxsize=1)
def _get_intent_model():
    """懒加载意图识别模型，从 YAML 配置读取参数（使用新的模型管理）"""
    cfg = get_main_workflow_config()
    params = find_node_by_id(cfg, "intent_router").get("params", {})

    model_name = params.get("model", DefaultConfig.DEFAULT_INTENT_MODEL)
    temperature = params.get("temperature", DefaultConfig.DEFAULT_INTENT_TEMPERATURE)

    return create_model_auto(
        model_name=model_name,
        temperature=temperature,
        credential_name="default"
    )


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
