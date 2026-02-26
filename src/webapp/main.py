# main.py - FastAPI入口
from fastapi import FastAPI, Request, HTTPException
from .routers import router
from src.agent.graph import graph

app = FastAPI(title="LangGraph FastAPI Agent")
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "graph": "agent ready"}

@app.get("/graphs")
async def graphs():
    return {"graphs": [{"id": "agent", "name": "OpenAI Tool Agent"}]}

@app.post("/runs/wait")
async def run_graph(request: Request):
    try:
        data = await request.json()
        graph_id = data.get("graph_id", "agent")
        input_data = data.get("input", {})
        # 只要走主graph即可，内部已调度
        result = await graph.ainvoke(input_data)
        return {
            "status": "success",
            "result": result,
            "graph_id": graph_id
        }
    except Exception as e:
        print(f"❌ Agent执行错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent执行失败: {str(e)}")
