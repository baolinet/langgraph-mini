#!/bin/bash
# sh ./test_api.sh - API 测试脚本
# 项目启动命令 uvicorn src.webapp.main:app --reload --host 0.0.0.0 --port 8000 或者 langgraph dev --no-browser

BASE_URL="http://localhost:8000"

echo "=== Health Check ==="
curl -s "$BASE_URL/health"

echo -e "\n\n=== Test 1: agent graph (default token) ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{"graph_id": "agent", "access_token": "token-alice", "input": {"messages": [{"role": "user", "content": "你好"}]}}'

echo -e "\n\n=== Test 2: order graph ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{"graph_id": "order", "access_token": "token-alice", "input": {"messages": [{"role": "user", "content": "查询订单"}]}}'

echo -e "\n\n=== Test 3: logistics graph ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{"graph_id": "logistics", "access_token": "token-alice", "input": {"messages": [{"role": "user", "content": "查询物流"}]}}'

echo -e "\n\n=== Test 4: invalid token ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{"graph_id": "agent", "access_token": "invalid-token", "input": {"messages": [{"role": "user", "content": "你好"}]}}'

echo -e "\n\n=== Test 5: invalid graph_id ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{"graph_id": "unknown", "access_token": "token-alice", "input": {"messages": [{"role": "user", "content": "你好"}]}}'

echo -e "\n\n=== Test 6: Mermaid graph ==="
curl -s "$BASE_URL/graphs/mermaid/all"

echo -e "\n\n=== Test 7: Complex task - write poem + fibonacci ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d '{"graph_id": "agent", "access_token": "token-alice", "input": {"messages": [{"role": "user", "content": "写一首关于AI Agent的中文诗，然后计算斐波那契数列第10项"}]}}'
