# logistics_graph.py - 物流处理workflow（使用 Tool Calling）
from .tools import tools_logistics, tools_dict
from .state import State
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import os
from dotenv import load_dotenv

load_dotenv(override=True)

model = ChatOpenAI(
    model="glm-4.7",
    temperature=0,
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY")
)

logistics_agent = create_react_agent(model, tools_logistics)


async def call_logistics_agent(state: State):
    """物流处理 Agent，使用 Tool Calling"""
    user_id = state["user_id"]
    messages = state["messages"]
    
    # 添加系统提示，引导 Agent 使用工具
    system_msg = f"""用户 ID 是 {user_id}。你需要查询用户的物流信息。
请按以下步骤操作：
1. 先使用 get_order_by_user_id 获取用户订单
2. 再使用 get_logistics_by_order_id 查询物流状态"""
    
    response = await logistics_agent.ainvoke({
        "messages": [
            {"role": "system", "content": system_msg},
            *messages
        ]
    })
    
    return {"messages": response["messages"]}


workflow = StateGraph(State)
workflow.add_node("logistics_agent", call_logistics_agent)
workflow.add_edge(START, "logistics_agent")
workflow.add_edge("logistics_agent", END)
logistics_graph = workflow.compile()
