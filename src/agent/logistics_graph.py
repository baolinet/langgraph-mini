# logistics_graph.py - 物流处理workflow（使用 Tool Calling + YAML配置）
from .tools import tools_logistics, tools_dict
from .state import State
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from .workflow_loader import get_logistics_workflow_config
import os
from dotenv import load_dotenv

load_dotenv(override=True)

config = get_logistics_workflow_config()
agent_config = config["agent"]
model_config = agent_config

model = ChatOpenAI(
    model=model_config.get("model", "glm-4.7"),
    temperature=model_config.get("temperature", 0),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY")
)

logistics_agent = create_react_agent(model, tools_logistics)


async def call_logistics_agent(state: State):
    """物流处理 Agent，使用 Tool Calling"""
    user_id = state["user_id"]
    messages = state["messages"]
    
    node_config = config["nodes"][0]
    system_msg_template = node_config.get("system_prompt", "用户 ID 是 {user_id}。你需要查询用户的物流信息。")
    system_msg = system_msg_template.format(user_id=user_id)
    
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
logistics_graph = workflow.compile(checkpointer=MemorySaver())
