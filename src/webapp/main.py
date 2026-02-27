# main.py - FastAPI入口
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.webapp.routers import router
from src.agent import GRAPH_REGISTRY, resolve_user_by_token

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

@app.get("/health")
async def health():
    return {"status": "healthy", "graph": "agent ready"}

@app.post("/runs/wait")
async def run_graph(body: RunRequest):
    target_graph = GRAPH_REGISTRY.get(body.graph_id)
    if target_graph is None:
        raise HTTPException(status_code=404, detail=f"未知的 graph_id: {body.graph_id}，可选值: {list(GRAPH_REGISTRY.keys())}")

    user_info = resolve_user_by_token(body.access_token)
    if user_info is None:
        raise HTTPException(status_code=401, detail="无效的 access_token，请重新登录")

    try:
        input_data = {
            **body.input.model_dump(),
            "user_id": user_info["user_id"],
        }
        logger.info(f"User authenticated: user_id={user_info['user_id']}, user_name={user_info['user_name']}, graph_id={body.graph_id}")

        result = await target_graph.ainvoke(input_data)
        return {
            "status": "success",
            "result": result,
            "graph_id": body.graph_id,
            "user_id": user_info["user_id"],
        }
    except Exception as e:
        logger.error(f"Agent execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent执行失败: {str(e)}")
