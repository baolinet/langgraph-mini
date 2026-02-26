# main.py - FastAPI入口
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from .routers import router
from src.agent.graph import graph
from src.agent.order_graph import order_graph
from src.agent.logistics_graph import logistics_graph
from src.agent.tools import resolve_user_by_token

# 图注册表，与 langgraph.json 中的 graph_id 对应
GRAPH_REGISTRY = {
    "agent":     graph,
    "order":     order_graph,
    "logistics": logistics_graph,
}

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
        # 跳过 --- front-matter 和 graph TD/TB 声明行，只保留节点和边
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
    # 手动补充跨图路由边（intent_router → 子图入口）
    combined += "agent:::default\n"
    combined += "intent_router -->|order| order\n"
    combined += "intent_router -->|logistics| logistics\n"
    return {"status": "success", "mermaid": combined}

@app.get("/health")
async def health():
    return {"status": "healthy", "graph": "agent ready"}

@app.post("/runs/wait")
async def run_graph(body: RunRequest):
    # 1. 校验 graph_id
    target_graph = GRAPH_REGISTRY.get(body.graph_id)
    if target_graph is None:
        return {"status": "failure", "result": {"detail": f"未知的 graph_id: {body.graph_id}，可选值: {list(GRAPH_REGISTRY.keys())}"}}

    # 2. 根据 access_token 解析用户身份
    user_info = resolve_user_by_token(body.access_token)
    if user_info is None:
        return {"status": "failure", "result": {"detail": "无效的 access_token，请重新登录"}}

    try:
        # 3. 构造 graph 输入，注入 user_id
        input_data = {
            **body.input.model_dump(),
            "user_id": user_info["user_id"],
        }
        print(f"🔑 用户已鉴权: user_id={user_info['user_id']}, user_name={user_info['user_name']}, graph_id={body.graph_id}")

        # 4. 按 graph_id 路由到对应的图
        result = await target_graph.ainvoke(input_data)
        return {
            "status": "success",
            "result": result,
            "graph_id": body.graph_id,
            "user_id": user_info["user_id"],
        }
    except Exception as e:
        print(f"❌ Agent执行错误: {str(e)}")
        return {"status": "failure", "result": {"detail": f"Agent执行失败: {str(e)}"}}
