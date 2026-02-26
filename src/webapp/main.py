# main.py - FastAPI入口
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from .routers import router
from src.agent.graph import graph
from src.agent.tools import resolve_user_by_token


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

@app.get("/health")
async def health():
    return {"status": "healthy", "graph": "agent ready"}

@app.get("/graphs")
async def graphs():
    return {"graphs": [{"id": "agent", "name": "OpenAI Tool Agent"}]}

@app.post("/runs/wait")
async def run_graph(body: RunRequest):
    # 1. 根据 access_token 解析用户身份
    user_info = resolve_user_by_token(body.access_token)
    if user_info is None:
        return {"status": "failure", "result": {"detail": "无效的 access_token，请重新登录"}}

    try:
        # 2. 构造 graph 输入，注入 user_id
        input_data = {
            **body.input.model_dump(),
            "user_id": user_info["user_id"],
        }
        print(f"🔑 用户已鉴权: user_id={user_info['user_id']}, user_name={user_info['user_name']}")

        # 3. 调用 graph，内部通过 state["user_id"] 获取身份
        result = await graph.ainvoke(input_data)
        return {
            "status": "success",
            "result": result,
            "graph_id": body.graph_id,
            "user_id": user_info["user_id"],
        }
    except Exception as e:
        print(f"❌ Agent执行错误: {str(e)}")
        return {"status": "failure", "result": {"detail": f"Agent执行失败: {str(e)}"}}
