#!/bin/bash
# sh ./test_api.sh - API 测试脚本
# 项目启动命令 uvicorn src.webapp.main:app --reload --host 0.0.0.0 --port 8000 或者 langgraph dev --no-browser

BASE_URL="http://localhost:8000"
SESSION_TOKEN="test-session-001"

echo "=== Health Check ==="
curl -s "$BASE_URL/health"

echo -e "\n\n=== Test 1: First message with session ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d "{\"graph_id\": \"agent\", \"access_token\": \"token-alice\", \"session_token\": \"$SESSION_TOKEN\", \"input\": {\"messages\": [{\"role\": \"user\", \"content\": \"我叫小明\"}]}}"

echo -e "\n\n=== Test 2: Second message (should have history) ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d "{\"graph_id\": \"agent\", \"access_token\": \"token-alice\", \"session_token\": \"$SESSION_TOKEN\", \"input\": {\"messages\": [{\"role\": \"user\", \"content\": \"我叫什么名字？\"}]}}"

echo -e "\n\n=== Test 3: Get session history ==="
curl -s "$BASE_URL/sessions/$SESSION_TOKEN"

echo -e "\n\n=== Test 4: Clear session ==="
curl -s -X DELETE "$BASE_URL/sessions/$SESSION_TOKEN"

echo -e "\n\n=== Test 5: Complex task (no session) ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d "{\"graph_id\": \"agent\", \"access_token\": \"token-alice\", \"input\": {\"messages\": [{\"role\": \"user\", \"content\": \"写一首关于AI Agent的中文诗\"}]}}"

echo -e "\n\n=== Test 6: order graph ==="
curl -s -X POST "$BASE_URL/runs/wait" \
  -H "Content-Type: application/json" \
  -d "{\"graph_id\": \"order\", \"access_token\": \"token-alice\", \"input\": {\"messages\": [{\"role\": \"user\", \"content\": \"查询订单\"}]}}"

echo -e "\n\n=== Test 7: Mermaid graph ==="
curl -s "$BASE_URL/graphs/mermaid/all"
