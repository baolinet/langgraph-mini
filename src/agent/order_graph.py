# order_graph.py - 订单处理workflow（使用 Tool Calling + YAML配置）
from .tools import tools_order, tools_dict
from .state import State
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from .workflow_loader import get_order_workflow_config
import os
from dotenv import load_dotenv

load_dotenv(override=True)

config = get_order_workflow_config()
agent_config = config["agent"]
model_config = agent_config

model = ChatOpenAI(
    model=model_config.get("model", "glm-4.7"),
    temperature=model_config.get("temperature", 0),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY")
)

order_agent = create_react_agent(model, tools_order)


async def call_order_agent(state: State):
    """订单处理 Agent，使用 Tool Calling"""
    user_id = state["user_id"]
    messages = state["messages"]
    
    node_config = config["nodes"][0]
    system_msg_template = node_config.get("system_prompt", "用户 ID 是 {user_id}。你需要查询用户的订单信息。请使用 get_order_by_user_id 工具查询。")
    system_msg = system_msg_template.format(user_id=user_id)
    
    response = await order_agent.ainvoke({
        "messages": [
            {"role": "system", "content": system_msg},
            *messages
        ]
    })
    
    return {"messages": response["messages"]}


workflow = StateGraph(State)
workflow.add_node("order_agent", call_order_agent)
workflow.add_edge(START, "order_agent")
workflow.add_edge("order_agent", END)
order_graph = workflow.compile(checkpointer=MemorySaver())
