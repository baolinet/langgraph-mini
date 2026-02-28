# main.py - FastAPI入口
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.webapp.routers import router
from src.agent import GRAPH_REGISTRY, resolve_user_by_token
from src.auth import create_session_token

# session_token -> 实际 thread_id 的映射表
# 清空会话时重新生成 thread_id，绕过 MemorySaver 不支持删除的限制
_session_thread_ids: dict[str, str] = {}

def _get_thread_id(session_token: str) -> str:
    """获取 session_token 对应的实际 thread_id"""
    return _session_thread_ids.get(session_token, session_token)

def _reset_thread_id(session_token: str) -> str:
    """清空会话：将 session_token 映射到新的 thread_id"""
    from datetime import datetime
    new_id = f"{session_token}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    _session_thread_ids[session_token] = new_id
    return new_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str

class RunInput(BaseModel):
    messages: list[Message]

class RunRequest(BaseModel):
    graph_id: Optional[str] = "agent"
    access_token: str = "token-alice"
    session_token: Optional[str] = None
    input: RunInput

app = FastAPI(title="LangGraph FastAPI Agent")
app.include_router(router)


@app.get("/graphs/mermaid/all")
async def all_graphs_mermaid():
    combined = "graph TB\n"
    for name, g in GRAPH_REGISTRY.items():
        mermaid_lines = g.get_graph().draw_mermaid().splitlines()
        body_lines = [
            line for line in mermaid_lines
            if line.strip() and not line.strip().startswith("---")
            and not line.strip().startswith("graph ")
            and not line.strip().startswith("config")
            and not line.strip().startswith("flowchart")
            and not line.strip().startswith("curve")
        ]
        combined += f"subgraph {name}\n"
        combined += "\n".join(body_lines) + "\n"
        combined += "end\n"
    combined += "agent:::default\n"
    combined += "intent_router -->|order| order\n"
    combined += "intent_router -->|logistics| logistics\n"
    return {"status": "success", "mermaid": combined}

@app.post("/runs/wait")
async def run_graph(body: RunRequest):
    from src.agent.graph import checkpointer
    
    target_graph = GRAPH_REGISTRY.get(body.graph_id)
    if target_graph is None:
        raise HTTPException(status_code=404, detail=f"未知的 graph_id: {body.graph_id}，可选值: {list(GRAPH_REGISTRY.keys())}")

    user_info = resolve_user_by_token(body.access_token)
    if user_info is None:
        raise HTTPException(status_code=401, detail="无效的 access_token，请重新登录")

    session_token = body.session_token
    if session_token is None:
        session_token = create_session_token(user_info["user_id"])

    try:
        from langchain_core.messages import HumanMessage

        thread_id = _get_thread_id(session_token)
        config = {"configurable": {"thread_id": thread_id}}
        
        existing_state = target_graph.get_state(config)
        if existing_state and existing_state.values:
            history_messages = list(existing_state.values.get("messages", []))
        else:
            history_messages = []
        
        all_messages = list(history_messages)
        for msg in body.input.messages:
            all_messages.append(HumanMessage(content=msg.content))
        
        input_data = {
            "messages": all_messages,
            "user_id": user_info["user_id"],
        }
        logger.info(f"User authenticated: user_id={user_info['user_id']}, user_name={user_info['user_name']}, graph_id={body.graph_id}, session={session_token}, history_count={len(history_messages)}")

        result = await target_graph.ainvoke(input_data, config=config)
        
        new_state = target_graph.get_state(config)
        if new_state and new_state.values:
            final_messages = new_state.values.get("messages", [])
            final_count = len(final_messages)
        else:
            final_count = 0
        
        return {
            "status": "success",
            "result": result,
            "graph_id": body.graph_id,
            "user_id": user_info["user_id"],
            "session_token": session_token,
            "history_count": final_count
        }
    except Exception as e:
        logger.error(f"Agent execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent执行失败: {str(e)}")

@app.get("/sessions/{session_token}")
async def get_session_history(session_token: str, graph_id: str = "agent"):
    """获取会话历史（从 LangGraph checkpointer 读取）"""
    target_graph = GRAPH_REGISTRY.get(graph_id)
    if target_graph is None:
        raise HTTPException(status_code=404, detail=f"未知的 graph_id: {graph_id}")

    thread_id = _get_thread_id(session_token)
    config = {"configurable": {"thread_id": thread_id}}
    state = target_graph.get_state(config)

    messages = []
    if state and state.values:
        for msg in state.values.get("messages", []):
            role = "user" if getattr(msg, "type", "") == "human" else "assistant"
            content = msg.content if hasattr(msg, "content") else str(msg)
            messages.append({"role": role, "content": content})

    return {
        "status": "success",
        "session_token": session_token,
        "messages": messages
    }

@app.post("/sessions/{session_token}/clear")
async def clear_session(session_token: str):
    """清空会话历史（重置 thread_id，下次对话从头开始）"""
    _reset_thread_id(session_token)
    return {"status": "success", "message": "会话已清空"}
