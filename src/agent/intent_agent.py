# intent_agent.py - 意图识别Agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, BaseMessage
import os
from dotenv import load_dotenv

load_dotenv(override=True)

async def intent_classify(messages: list[BaseMessage]):
    """调用大模型识别意图，返回intent: order/logistics/other"""
    model = ChatOpenAI(
        model="kimi-k2-thinking",
        temperature=0,
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    prompt = "请判断用户问题属于以下哪一类：订单问题、物流问题、无关问题。只返回order/logistics/other。用户问题：" + messages[-1].content
    resp = await model.ainvoke([AIMessage(content=prompt)])
    intent = resp.content.strip().lower()
    if "订单" in intent or "order" in intent:
        return "order"
    if "物流" in intent or "logistics" in intent:
        return "logistics"
    return "other"
