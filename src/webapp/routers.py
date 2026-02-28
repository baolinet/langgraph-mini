# routers.py - 统一 API 路由
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from src.agent import GRAPH_REGISTRY, resolve_user_by_token
from src.auth import create_session_token

logger = logging.getLogger(__name__)
router = APIRouter()

# ── 会话 thread_id 映射（带 TTL 自动清理，防止内存泄漏） ──────────────────────
_SESSION_MAP_TTL = timedelta(hours=24)
_session_thread_map: dict[str, tuple[str, datetime]] = {}


def _get_thread_id(session_token: str) -> str:
    """获取 session_token 对应的实际 thread_id"""
    entry = _session_thread_map.get(session_token)
    return entry[0] if entry else session_token


def _reset_thread_id(session_token: str) -> str:
    """重置 thread_id（清空会话时调用），同时清理过期条目"""
    _cleanup_expired_sessions()
    new_id = f"{session_token}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    _session_thread_map[session_token] = (new_id, datetime.now())
    return new_id


def _cleanup_expired_sessions() -> None:
    """删除超过 TTL 的会话映射条目"""
    now = datetime.now()
    expired = [k for k, (_, ts) in _session_thread_map.items() if now - ts > _SESSION_MAP_TTL]
    for k in expired:
        del _session_thread_map[k]


# ── Pydantic 请求模型 ──────────────────────────────────────────────────────────
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


# ── 基础路由 ───────────────────────────────────────────────────────────────────
@router.get("/")
def index():
    return {"msg": "hello world"}


@router.get("/ping")
def ping():
    return {"msg": "pong"}


@router.get("/health")
async def health():
    return {"status": "healthy", "graph": "agent ready"}


# ── Graph 路由 ─────────────────────────────────────────────────────────────────
@router.get("/graphs/mermaid/all")
async def all_graphs_mermaid():
    """返回所有注册 Graph 的合并 Mermaid 图"""
    combined = "graph TB\n"
    for name, g in GRAPH_REGISTRY.items():
        mermaid_lines = g.get_graph().draw_mermaid().splitlines()
        body_lines = [
            line for line in mermaid_lines
            if line.strip()
            and not line.strip().startswith("---")
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


@router.post("/runs/wait")
async def run_graph(body: RunRequest):
    """执行 Graph 并等待结果"""
    target_graph = GRAPH_REGISTRY.get(body.graph_id)
    if target_graph is None:
        raise HTTPException(
            status_code=404,
            detail=f"未知的 graph_id: {body.graph_id}，可选值: {list(GRAPH_REGISTRY.keys())}",
        )

    user_info = resolve_user_by_token(body.access_token)
    if user_info is None:
        raise HTTPException(status_code=401, detail="无效的 access_token，请重新登录")

    session_token = body.session_token or create_session_token(user_info["user_id"])

    try:
        thread_id = _get_thread_id(session_token)
        run_config = {"configurable": {"thread_id": thread_id}}

        existing_state = target_graph.get_state(run_config)
        history_messages = (
            list(existing_state.values.get("messages", []))
            if existing_state and existing_state.values
            else []
        )

        all_messages = history_messages + [
            HumanMessage(content=m.content) for m in body.input.messages
        ]
        input_data = {"messages": all_messages, "user_id": user_info["user_id"]}

        logger.info(
            "User authenticated: user_id=%s, user_name=%s, graph_id=%s, "
            "session=%s, history_count=%d",
            user_info["user_id"], user_info["user_name"],
            body.graph_id, session_token, len(history_messages),
        )

        result = await target_graph.ainvoke(input_data, config=run_config)

        new_state = target_graph.get_state(run_config)
        final_count = (
            len(new_state.values.get("messages", []))
            if new_state and new_state.values
            else 0
        )

        return {
            "status": "success",
            "result": result,
            "graph_id": body.graph_id,
            "user_id": user_info["user_id"],
            "session_token": session_token,
            "history_count": final_count,
        }
    except Exception as e:
        logger.error("Agent execution error: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Agent执行失败: {str(e)}")


@router.get("/sessions/{session_token}")
async def get_session_history(session_token: str, graph_id: str = "agent"):
    """获取会话历史（从 LangGraph checkpointer 读取）"""
    target_graph = GRAPH_REGISTRY.get(graph_id)
    if target_graph is None:
        raise HTTPException(status_code=404, detail=f"未知的 graph_id: {graph_id}")

    run_config = {"configurable": {"thread_id": _get_thread_id(session_token)}}
    state = target_graph.get_state(run_config)

    messages = []
    if state and state.values:
        for msg in state.values.get("messages", []):
            role = "user" if getattr(msg, "type", "") == "human" else "assistant"
            content = msg.content if hasattr(msg, "content") else str(msg)
            messages.append({"role": role, "content": content})

    return {"status": "success", "session_token": session_token, "messages": messages}


@router.post("/sessions/{session_token}/clear")
async def clear_session(session_token: str):
    """清空会话历史（重置 thread_id，下次对话从头开始）"""
    _reset_thread_id(session_token)
    return {"status": "success", "message": "会话已清空"}