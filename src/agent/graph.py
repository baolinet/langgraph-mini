# graph.py - LangGraph Agent定义
from .tools import tools, tools_dict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

async def call_model(state: State):
    model = ChatOpenAI(
        model="kimi-k2-thinking",
        temperature=0,
        base_url=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    model_with_tools = model.bind_tools(tools)
    response = await model_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}

async def execute_tools(state: State):
    last_message = state["messages"][-1]
    results = []
    tool_calls = getattr(last_message, 'tool_calls', [])
    for tool_call in tool_calls:
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        tool_func = tools_dict.get(tool_name, lambda x: "未知工具")
        tool_result = tool_func.invoke(tool_args)
        results.append(AIMessage(
            content=str(tool_result),
            tool_call_id=tool_call['id']
        ))
    return {"messages": results}

def should_continue(state: State):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow = StateGraph(State)
workflow.add_node("agent", call_model)
workflow.add_node("tools", execute_tools)
workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {
    "tools": "tools",
    END: END
})
workflow.add_edge("tools", "agent")
graph = workflow.compile()
