# intent_agent.py - 意图识别Agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def intent_classify(messages: list[BaseMessage]):
    """调用大模型识别意图，返回intent: order/logistics/general/other"""
    model = ChatOpenAI(
        model="kimi-k2-thinking",
        temperature=0,
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    last_message = messages[-1].content if messages else ""
    prompt = f"""请判断用户问题属于以下哪一类：
- 订单问题（如查询订单、订单状态、取消订单等）：返回 order
- 物流问题（如查询物流、快递信息、物流状态等）：返回 logistics  
- 通用对话或任务（如写诗、计算、问答、聊天等）：返回 general
- 无关问题（垃圾信息、无意义内容等）：返回 other

只返回其中一个词：order/logistics/general/other，不要返回其他内容。

用户问题：{last_message}"""
    resp = await model.ainvoke([HumanMessage(content=prompt)])
    intent = str(resp.content).strip().lower()
    
    if "订单" in intent or "order" in intent:
        return "order"
    if "物流" in intent or "logistics" in intent:
        return "logistics"
    if "通用" in intent or "general" in intent or "对话" in intent or "任务" in intent:
        return "general"
    return "other"
