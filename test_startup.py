#!/usr/bin/env python
"""测试项目启动和模块导入"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🚀 测试项目启动...")
print()

# 测试 1: LLM 模块
print("1️⃣  测试 LLM 模块导入...")
try:
    from src.llm import (
        Provider,
        Credential,
        ModelConfig,
        create_model_auto,
        create_model_from_yaml,
        default_credential_manager,
        default_model_factory,
    )
    print("   ✅ LLM 模块导入成功")
    print(f"   - 支持的供应商: {len([p for p in Provider])}")
except Exception as e:
    print(f"   ❌ LLM 模块导入失败: {e}")
    sys.exit(1)

# 测试 2: 数据库模块
print("\n2️⃣  测试数据库模块...")
try:
    from src.db import get_db
    db = get_db(":memory:")
    providers = db.list_providers()
    print(f"   ✅ 数据库模块测试成功")
    print(f"   - 预置供应商: {len(providers)} 个")
except Exception as e:
    print(f"   ❌ 数据库模块失败: {e}")
    sys.exit(1)

# 测试 3: Agent 模块
print("\n3️⃣  测试 Agent 模块...")
try:
    from src.agent import GRAPH_REGISTRY
    from src.agent.intent_agent import intent_classify
    from src.agent.graph_factory import build_tool_agent_graph
    print("   ✅ Agent 模块导入成功")
    print(f"   - 注册的 Graph: {list(GRAPH_REGISTRY.keys())}")
except Exception as e:
    print(f"   ❌ Agent 模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 4: FastAPI 应用
print("\n4️⃣  测试 FastAPI 应用...")
try:
    from src.webapp.main import app
    print("   ✅ FastAPI 应用加载成功")
    print(f"   - 应用标题: {app.title}")
except Exception as e:
    print(f"   ❌ FastAPI 应用加载失败: {e}")
    sys.exit(1)

# 测试 5: 模型创建
print("\n5️⃣  测试模型创建...")
try:
    # 测试从 YAML 创建（兼容旧配置）
    yaml_config = {"model": "gpt-4o-mini", "temperature": 0.7}
    model = create_model_from_yaml(yaml_config, cache_key="test_model")
    print("   ✅ 从 YAML 创建模型成功")

    # 测试自动创建
    model2 = create_model_auto("gpt-4o-mini", temperature=0.8)
    print("   ✅ 自动创建模型成功")
except Exception as e:
    print(f"   ⚠️  模型创建警告: {e}")
    print("   (这可能是因为未设置 OPENAI_API_KEY)")

# 测试 6: 配置加载
print("\n6️⃣  测试配置加载...")
try:
    from src.agent.workflow_loader import (
        get_main_workflow_config,
        get_order_workflow_config,
        get_logistics_workflow_config,
    )
    main_cfg = get_main_workflow_config()
    order_cfg = get_order_workflow_config()
    logistics_cfg = get_logistics_workflow_config()
    print("   ✅ 配置加载成功")
    print(f"   - Main workflow: {main_cfg.get('name')}")
    print(f"   - Order workflow: {order_cfg.get('name')}")
    print(f"   - Logistics workflow: {logistics_cfg.get('name')}")
except Exception as e:
    print(f"   ❌ 配置加载失败: {e}")
    sys.exit(1)

print("\n" + "="*50)
print("✨ 所有测试通过！项目启动正常。")
print("="*50)
print("\n💡 下一步:")
print("   1. 运行应用: uvicorn src.webapp.main:app --reload")
print("   2. 或使用: langgraph dev --no-browser")
print("   3. 测试 API: sh ./test_api.sh")
print()
