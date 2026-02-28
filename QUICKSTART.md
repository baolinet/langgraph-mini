# 🚀 快速开始指南 - 新模型管理系统

## 📖 概述

本指南帮助你快速上手新的模型管理系统，实现：
- ✅ 为不同节点配置不同模型
- ✅ 使用多个 LLM 供应商
- ✅ 管理多套 API 凭证
- ✅ 追踪模型使用统计

---

## 🎯 5分钟快速开始

### Step 1: 初始化数据库

```python
from src.db import get_db

# 自动创建表结构和预置数据
db = get_db("langgraph.db")
print("数据库初始化完成！")
```

### Step 2: 查看预置供应商

```python
# 列出所有支持的供应商
providers = db.list_providers()
for p in providers:
    print(f"{p['name']}: {p['display_name']}")

# 输出：
# openai: OpenAI
# zhipu: 智谱 AI
# moonshot: Moonshot AI
# deepseek: DeepSeek
# ...
```

### Step 3: 使用新的模型创建方式

```python
from src.llm import create_model_auto

# 方式1: 自动推断供应商（推荐）
model = create_model_auto("gpt-4o-mini", temperature=0.7)

# 方式2: 智谱 GLM
model = create_model_auto("glm-4-flash", temperature=0.0)

# 方式3: Moonshot Kimi
model = create_model_auto("moonshot-v1-8k", temperature=0.8)

# 开始使用
response = await model.ainvoke("Hello!")
```

### Step 4: 配置节点使用不同模型

```python
# 1. 创建模型配置
model_id = db.create_model({
    "name": "fast_intent_model",
    "model_name": "glm-4-flash",
    "provider_id": 2,  # 智谱
    "credential_id": 1,
    "temperature": 0.0,
    "display_name": "快速意图分类模型",
    "description": "用于意图识别的轻量级模型"
})

# 2. 获取节点ID
nodes = db.execute_query(
    "SELECT id FROM workflow_nodes WHERE workflow_name='main' AND node_id='intent_router'"
)
node_id = nodes[0]["id"]

# 3. 绑定节点和模型
db.execute_insert(
    "INSERT INTO node_model_configs (node_id, model_id, priority) VALUES (?, ?, ?)",
    (node_id, model_id, 100)
)

print(f"成功配置节点 intent_router 使用模型 glm-4-flash")
```

### Step 5: 查询节点模型配置

```python
# 获取特定节点的模型配置
config = db.get_node_model_config("main", "intent_router")
print(f"节点使用的模型: {config['model_name']}")
print(f"供应商: {config['provider_name']}")
print(f"温度: {config['temperature']}")
```

---

## 💡 常见使用场景

### 场景1: 为不同节点配置不同模型

**需求**: 意图识别用快速模型，订单处理用准确模型

```python
# 配置意图识别节点
db.create_model({
    "name": "intent_model",
    "model_name": "glm-4-flash",      # 快速模型
    "provider_id": 2,
    "credential_id": 1,
    "temperature": 0.0,
})

# 配置订单处理节点
db.create_model({
    "name": "order_model",
    "model_name": "gpt-4o",           # 准确模型
    "provider_id": 1,
    "credential_id": 1,
    "temperature": 0.7,
})

# 绑定节点
# ... (参考 Step 4)
```

### 场景2: 切换供应商

**需求**: 从 OpenAI 切换到智谱 AI

```python
# 旧代码（自动兼容）
model = create_model_auto("gpt-4o")

# 新代码
model = create_model_auto("glm-4-plus")  # 直接改模型名即可
```

### 场景3: 管理多套凭证

**需求**: 生产和测试使用不同的 API Key

```python
from src.llm import default_credential_manager, Credential, Provider

# 添加生产凭证
prod_cred = Credential(
    provider=Provider.OPENAI,
    api_key="sk-prod-xxx",
    name="prod",
    description="生产环境凭证"
)
default_credential_manager.add_credential("prod", prod_cred)

# 添加测试凭证
test_cred = Credential(
    provider=Provider.OPENAI,
    api_key="sk-test-xxx",
    name="test",
    description="测试环境凭证"
)
default_credential_manager.add_credential("test", test_cred)

# 使用特定凭证创建模型
from src.llm import ModelConfig, default_model_factory

config = ModelConfig(
    model_name="gpt-4o",
    provider=Provider.OPENAI,
    credential_name="prod",  # 使用生产凭证
    temperature=0.7
)
model = default_model_factory.create_model(config)
```

### 场景4: 追踪模型使用

**需求**: 统计每个模型的 token 使用量

```python
# 在调用模型后记录使用情况
db.log_model_usage({
    "model_id": 1,
    "node_id": 1,
    "user_id": "user-001",
    "session_id": "session-123",
    "input_tokens": 150,
    "output_tokens": 300,
    "total_tokens": 450,
    "duration_ms": 1500,
    "status": "success"
})

# 查询统计
stats = db.execute_query("""
    SELECT
        m.name,
        COUNT(*) as call_count,
        SUM(total_tokens) as total_tokens,
        AVG(duration_ms) as avg_duration
    FROM model_usage_logs l
    JOIN models m ON l.model_id = m.id
    WHERE l.created_at >= datetime('now', '-7 days')
    GROUP BY m.name
""")

for stat in stats:
    print(f"{stat['name']}: {stat['call_count']} 次调用, {stat['total_tokens']} tokens")
```

---

## 🔧 高级用法

### 1. 自定义供应商

```python
from src.llm import Provider, Credential, ModelConfig, default_model_factory

# 添加自定义供应商凭证
custom_cred = Credential(
    provider=Provider.CUSTOM,
    api_key="your-api-key",
    base_url="https://your-api-endpoint.com/v1",
    name="custom_provider"
)
default_credential_manager.add_credential("custom", custom_cred)

# 创建模型
config = ModelConfig(
    model_name="your-model-name",
    provider=Provider.CUSTOM,
    credential_name="custom",
    temperature=0.7
)
model = default_model_factory.create_model(config)
```

### 2. 条件路由（高级）

**需求**: 付费用户使用 GPT-4，免费用户使用 GPT-3.5

```python
# 配置两个模型
premium_model_id = db.create_model({
    "name": "premium_model",
    "model_name": "gpt-4o",
    ...
})

free_model_id = db.create_model({
    "name": "free_model",
    "model_name": "gpt-3.5-turbo",
    ...
})

# 绑定到同一节点，设置条件
db.execute_insert("""
    INSERT INTO node_model_configs (node_id, model_id, priority, conditions)
    VALUES (?, ?, ?, ?)
""", (
    node_id,
    premium_model_id,
    100,
    '{"user_type": "premium"}'  # 条件：付费用户
))

db.execute_insert("""
    INSERT INTO node_model_configs (node_id, model_id, priority, conditions)
    VALUES (?, ?, ?, ?)
""", (
    node_id,
    free_model_id,
    50,
    '{"user_type": "free"}'  # 条件：免费用户
))

# 在代码中根据条件选择模型
# TODO: 实现条件匹配逻辑
```

### 3. 模型降级策略

```python
# 配置主模型和备用模型
primary_model_id = db.create_model({
    "name": "primary_gpt4",
    "model_name": "gpt-4o",
    ...
})

fallback_model_id = db.create_model({
    "name": "fallback_gpt35",
    "model_name": "gpt-3.5-turbo",
    ...
})

# 绑定优先级
db.execute_insert(
    "INSERT INTO node_model_configs (node_id, model_id, priority) VALUES (?, ?, ?)",
    (node_id, primary_model_id, 100)  # 高优先级
)
db.execute_insert(
    "INSERT INTO node_model_configs (node_id, model_id, priority) VALUES (?, ?, ?)",
    (node_id, fallback_model_id, 50)  # 低优先级（降级使用）
)

# 在代码中实现降级逻辑
try:
    result = await primary_model.ainvoke(...)
except Exception as e:
    logger.warning(f"主模型失败，使用备用模型: {e}")
    result = await fallback_model.ainvoke(...)
```

---

## 📊 监控和运维

### 查看所有模型配置

```python
models = db.execute_query("""
    SELECT
        m.name,
        m.model_name,
        p.display_name as provider,
        c.name as credential,
        m.temperature,
        m.is_active
    FROM models m
    JOIN providers p ON m.provider_id = p.id
    JOIN credentials c ON m.credential_id = c.id
    ORDER BY m.name
""")

for m in models:
    print(f"{m['name']}: {m['model_name']} ({m['provider']}) - Active: {m['is_active']}")
```

### 查看节点模型映射

```python
mappings = db.execute_query("""
    SELECT
        n.workflow_name,
        n.node_id,
        m.model_name,
        p.display_name as provider,
        nmc.priority
    FROM node_model_configs nmc
    JOIN workflow_nodes n ON nmc.node_id = n.id
    JOIN models m ON nmc.model_id = m.id
    JOIN providers p ON m.provider_id = p.id
    WHERE nmc.is_active = 1
    ORDER BY n.workflow_name, n.node_id, nmc.priority DESC
""")

for mapping in mappings:
    print(f"{mapping['workflow_name']}.{mapping['node_id']} -> {mapping['model_name']}")
```

### 成本分析

```python
# 计算过去7天的 token 使用量
cost_data = db.execute_query("""
    SELECT
        m.name,
        m.model_name,
        SUM(l.input_tokens) as total_input,
        SUM(l.output_tokens) as total_output,
        SUM(l.total_tokens) as total_tokens,
        COUNT(*) as call_count
    FROM model_usage_logs l
    JOIN models m ON l.model_id = m.id
    WHERE l.created_at >= datetime('now', '-7 days')
    GROUP BY m.id
    ORDER BY total_tokens DESC
""")

# 假设 GPT-4 价格: $0.03/1K input, $0.06/1K output
for data in cost_data:
    if "gpt-4" in data["model_name"]:
        cost = (data["total_input"] / 1000 * 0.03 +
                data["total_output"] / 1000 * 0.06)
        print(f"{data['name']}: ${cost:.2f} (估算)")
```

---

## 🔄 迁移清单

从旧系统迁移到新系统的步骤：

- [ ] 1. 初始化数据库 (`get_db()`)
- [ ] 2. 导入现有凭证到数据库
- [ ] 3. 测试新的模型创建方式 (`create_model_auto`)
- [ ] 4. 配置各节点的模型映射
- [ ] 5. 更新代码使用新 API（可选，兼容旧代码）
- [ ] 6. 添加使用日志记录
- [ ] 7. 设置监控和告警

---

## 🆘 常见问题

### Q1: 旧代码还能运行吗？
**A**: 可以！新架构完全向后兼容，现有代码无需修改。

### Q2: 如何从环境变量切换到数据库配置？
**A**: 渐进式迁移。可以先用环境变量，再逐步将凭证导入数据库。

### Q3: 模型实例会被缓存吗？
**A**: 会！相同配置的模型会被缓存复用，提高性能。

### Q4: 如何清空模型缓存？
```python
from src.llm import default_model_factory
default_model_factory.clear_cache()
```

### Q5: 数据库文件在哪里？
**A**: 默认是项目根目录的 `langgraph.db`，可以通过 `get_db("自定义路径")` 修改。

### Q6: 如何备份配置？
```bash
# SQLite 数据库直接复制文件即可
cp langgraph.db langgraph.db.backup
```

---

## 📚 更多资源

- **详细文档**: 查看 `REFACTORING_SUMMARY.md`
- **数据库说明**: 查看 `src/db/README.md`
- **API 参考**: 查看各模块的 docstring
- **示例代码**: 查看 `tests/` 目录（TODO）

---

**祝使用愉快！有问题随时查看文档或提 Issue。🎉**
