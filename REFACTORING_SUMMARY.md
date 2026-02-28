# 🔄 项目重构总结

**重构日期**: 2026-02-28
**目标**: 优化模型管理架构，支持多供应商、多凭证、节点级模型配置

---

## 📋 问题分析

### 原有问题

1. **graph_factory.py 设计缺陷**
   - 函数签名存在无效的孤立星号 `*,`
   - 模型配置硬编码，每次调用创建新实例
   - 只支持 OpenAI 兼容接口
   - 凭证从环境变量硬编码获取
   - 无法为不同节点配置不同模型

2. **代码重复严重**
   - `graph_factory.py`、`intent_agent.py`、`general_graph.py` 都有类似的模型创建代码
   - 违反 DRY 原则

3. **缺乏灵活性**
   - 无法动态切换供应商
   - 无法支持多套凭证配置
   - 扩展性差

---

## ✅ 重构方案

### 1. 创建 LLM 管理模块 (`src/llm/`)

#### 1.1 Provider 管理 (`provider.py`)

**核心功能**:
- 定义 `Provider` 枚举（OpenAI、智谱、Moonshot、DeepSeek、Anthropic 等）
- 提供 `ProviderConfig` 配置类
- 预定义供应商默认配置和支持的模型列表

**支持的供应商**:
```python
Provider.OPENAI          # OpenAI GPT 系列
Provider.ZHIPU           # 智谱 GLM 系列
Provider.MOONSHOT        # Moonshot Kimi 系列
Provider.DEEPSEEK        # DeepSeek 系列
Provider.ANTHROPIC       # Anthropic Claude 系列
Provider.AZURE_OPENAI    # Azure OpenAI
Provider.OLLAMA          # 本地模型
Provider.CUSTOM          # 自定义兼容服务
```

#### 1.2 凭证管理 (`credential.py`)

**核心功能**:
- `Credential` 数据类：存储 API Key、Base URL 等
- `CredentialManager`：统一管理多套凭证
- 自动从环境变量加载默认凭证
- 根据 URL 智能推断供应商

**特性**:
```python
# 支持多套凭证
credential_manager.add_credential("prod_openai", ...)
credential_manager.add_credential("test_openai", ...)
credential_manager.add_credential("zhipu_key", ...)

# 获取凭证
cred = credential_manager.get_credential("prod_openai")
```

#### 1.3 模型管理 (`model.py`)

**核心功能**:
- `ModelConfig` 数据类：定义模型配置
- `ModelFactory` 工厂类：创建和缓存模型实例
- 支持从 YAML 配置创建模型（兼容旧格式）
- 自动推断供应商

**便捷函数**:
```python
# 方式1: 从配置创建
config = ModelConfig(
    model_name="gpt-4o",
    provider=Provider.OPENAI,
    temperature=0.7
)
model = default_model_factory.create_model(config)

# 方式2: 自动推断供应商
model = create_model_auto("glm-4-plus", temperature=0.7)

# 方式3: 从 YAML 创建（兼容旧配置）
model = create_model_from_yaml(
    {"model": "gpt-4o", "temperature": 0.7},
    cache_key="my_model"
)
```

**模型缓存**:
- 相同配置的模型实例会被缓存复用
- 提高性能，减少初始化开销

---

### 2. 创建数据库模块 (`src/db/`)

#### 2.1 表结构设计 (`schema.sql`)

**核心表**:

1. **providers** - 供应商表
   - 预置 8 个供应商配置
   - 支持自定义供应商

2. **credentials** - 凭证表
   - 存储 API Key（TODO: 后续加密）
   - 支持 Azure 特殊字段（api_version、deployment_name）
   - 关联到供应商

3. **models** - 模型配置表
   - 存储完整的模型参数
   - 关联到供应商和凭证
   - 支持启用/禁用

4. **workflow_nodes** - 工作流节点表
   - 存储节点配置和 system_prompt
   - 按 workflow_name + node_id 组织

5. **node_model_configs** - 节点模型映射表 ⭐
   - **核心表**：实现每个节点使用不同模型
   - 支持优先级排序
   - 支持条件路由（JSON 配置）

6. **model_usage_logs** - 使用日志表
   - 记录 token 使用量
   - 追踪调用时长和状态
   - 支持成本分析

7. **tools** & **node_tool_mappings** - 工具表
   - 定义可用工具
   - 映射节点与工具

#### 2.2 数据库管理器 (`database.py`)

**核心功能**:
```python
from src.db import get_db

db = get_db()

# 查询供应商
providers = db.list_providers()
zhipu = db.get_provider_by_name("zhipu")

# 管理凭证
cred_id = db.create_credential({...})
cred = db.get_credential_by_name("my_key")

# 管理模型
model_id = db.create_model({...})
model = db.get_model_by_name("order_agent")

# 获取节点模型配置（核心）
config = db.get_node_model_config("order", "order_agent")

# 记录使用日志
db.log_model_usage({...})
```

---

### 3. 重构现有代码

#### 3.1 修复 `graph_factory.py`

**主要改动**:
1. ❌ 删除无效的 `*,` 参数
2. ✅ 添加 `model_config` 参数，支持传入自定义配置
3. ✅ 使用 `create_model_from_yaml` 创建模型（支持缓存）
4. ✅ 保持向后兼容（仍可从 YAML 创建）

**新签名**:
```python
def build_tool_agent_graph(
    workflow_config: Dict[str, Any],
    tools: list,
    use_checkpointer: bool = True,
    model_config: Optional[ModelConfig] = None,  # 新增
) -> Any:
```

#### 3.2 重构 `intent_agent.py`

**主要改动**:
1. ❌ 删除手动创建 `ChatOpenAI` 的代码
2. ✅ 使用 `create_model_auto` 自动创建模型
3. ✅ 使用 `@lru_cache` 装饰器缓存模型实例

**对比**:
```python
# 旧代码
_intent_model = ChatOpenAI(
    model=params.get("model", "kimi-k2-thinking"),
    temperature=params.get("temperature", 0.7),
    base_url=os.environ.get("OPENAI_BASE_URL"),
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# 新代码
model = create_model_auto(
    model_name=params.get("model", "kimi-k2-thinking"),
    temperature=params.get("temperature", 0.7),
    credential_name="default"
)
```

#### 3.3 重构 `general_graph.py`

**主要改动**:
- 与 `intent_agent.py` 类似
- 使用统一的模型创建方式
- 删除重复代码

---

## 🎯 核心特性

### 1. 每个节点可配置不同模型

**场景示例**:
```sql
-- 意图分类：使用快速模型
INSERT INTO models (name, model_name, provider_id, ...)
VALUES ('intent_model', 'kimi-k2-thinking', ...);

-- 订单处理：使用智谱模型
INSERT INTO models (name, model_name, provider_id, ...)
VALUES ('order_model', 'glm-4-flash', ...);

-- 物流处理：使用 DeepSeek
INSERT INTO models (name, model_name, provider_id, ...)
VALUES ('logistics_model', 'deepseek-chat', ...);

-- 映射节点到模型
INSERT INTO node_model_configs (node_id, model_id, priority)
VALUES (1, 1, 100), (2, 2, 100), (3, 3, 100);
```

**程序使用**:
```python
# 获取节点配置的模型
config = db.get_node_model_config("order", "order_agent")
# 返回: {model_name: "glm-4-flash", provider_name: "zhipu", ...}

# 创建模型实例
model_config = ModelConfig.from_dict(config)
model = default_model_factory.create_model(model_config)
```

### 2. 支持多供应商

**一键切换供应商**:
```python
# OpenAI
model1 = create_model_auto("gpt-4o")

# 智谱 AI
model2 = create_model_auto("glm-4-plus")

# Moonshot
model3 = create_model_auto("moonshot-v1-8k")

# 自动推断供应商，无需手动指定
```

### 3. 多凭证管理

**场景**:
- 生产环境使用付费 API Key
- 测试环境使用测试 API Key
- 不同项目使用不同账号

**实现**:
```python
# 添加多套凭证
credential_manager.add_credential("prod", ...)
credential_manager.add_credential("test", ...)
credential_manager.add_credential("backup", ...)

# 创建模型时指定凭证
config = ModelConfig(
    model_name="gpt-4o",
    credential_name="prod"  # 使用生产凭证
)
```

### 4. 模型使用统计

**自动记录**:
```python
db.log_model_usage({
    "model_id": 1,
    "user_id": "user-001",
    "input_tokens": 150,
    "output_tokens": 300,
    "duration_ms": 1500,
    "status": "success"
})
```

**分析查询**:
```sql
-- 每个模型的总 token 使用量
SELECT m.name, SUM(total_tokens) as total
FROM model_usage_logs l
JOIN models m ON l.model_id = m.id
GROUP BY m.name;

-- 每个用户的使用统计
SELECT user_id, COUNT(*) as calls, SUM(total_tokens) as total_tokens
FROM model_usage_logs
GROUP BY user_id;

-- 错误率统计
SELECT status, COUNT(*) as count
FROM model_usage_logs
GROUP BY status;
```

---

## 📦 项目结构变化

### 新增文件

```
src/
├── llm/                        # 新增：LLM 管理模块
│   ├── __init__.py
│   ├── provider.py             # 供应商管理
│   ├── credential.py           # 凭证管理
│   └── model.py                # 模型工厂
├── db/                         # 新增：数据库模块
│   ├── __init__.py
│   ├── schema.sql              # 数据库表结构
│   ├── database.py             # 数据库管理器
│   └── README.md               # 使用文档
└── agent/
    ├── graph_factory.py        # 重构
    ├── intent_agent.py         # 重构
    └── general_graph.py        # 重构
```

### 修改文件

- `src/agent/graph_factory.py` - 修复并增强
- `src/agent/intent_agent.py` - 使用新模型管理
- `src/agent/general_graph.py` - 使用新模型管理
- `src/agent/order_graph.py` - 无需修改（使用 graph_factory）
- `src/agent/logistics_graph.py` - 无需修改（使用 graph_factory）

---

## 🔄 迁移指南

### 1. 兼容性

**✅ 向后兼容**:
- 现有代码无需修改即可运行
- 仍然支持从环境变量读取凭证
- 仍然支持 YAML 配置格式

**🆕 渐进式迁移**:
- 可以逐步迁移到数据库配置
- 可以同时使用环境变量和数据库配置

### 2. 初始化数据库

```bash
# 方式1: 自动初始化（首次运行时）
python -c "from src.db import get_db; get_db()"

# 方式2: 在应用启动时初始化
# 在 main.py 中添加
from src.db import get_db
get_db()  # 确保数据库已初始化
```

### 3. 从环境变量导入凭证

```python
from src.db import get_db
from src.llm import default_credential_manager
import os

# 方式1: 使用 CredentialManager（自动导入）
# default_credential_manager 已自动从环境变量加载

# 方式2: 手动导入到数据库
db = get_db()
openai_provider = db.get_provider_by_name("openai")
db.create_credential({
    "name": "env_imported",
    "provider_id": openai_provider["id"],
    "api_key": os.getenv("OPENAI_API_KEY"),
    "base_url": os.getenv("OPENAI_BASE_URL"),
    "description": "从环境变量导入"
})
```

### 4. 配置节点模型

```python
from src.db import get_db

db = get_db()

# 1. 创建模型配置
model_id = db.create_model({
    "name": "my_custom_model",
    "model_name": "gpt-4o",
    "provider_id": 1,
    "credential_id": 1,
    "temperature": 0.8,
    "display_name": "自定义模型"
})

# 2. 查找节点ID
nodes = db.execute_query(
    "SELECT id FROM workflow_nodes WHERE workflow_name=? AND node_id=?",
    ("order", "order_agent")
)
node_id = nodes[0]["id"]

# 3. 绑定节点和模型
db.execute_insert(
    "INSERT INTO node_model_configs (node_id, model_id, priority) VALUES (?, ?, ?)",
    (node_id, model_id, 100)
)
```

---

## 📊 测试验证

### 1. 单元测试建议

```python
# tests/test_llm.py
def test_provider_config():
    config = get_provider_config(Provider.OPENAI)
    assert config.provider == Provider.OPENAI
    assert config.default_base_url is not None

def test_credential_creation():
    cred = Credential(
        provider=Provider.OPENAI,
        api_key="sk-test",
        base_url="https://api.openai.com/v1"
    )
    assert cred.api_key == "sk-test"

def test_model_factory():
    config = ModelConfig(
        model_name="gpt-4o",
        provider=Provider.OPENAI,
        temperature=0.7
    )
    model = default_model_factory.create_model(config)
    assert model is not None

# tests/test_db.py
def test_database_init():
    db = get_db(":memory:")  # 使用内存数据库测试
    providers = db.list_providers()
    assert len(providers) > 0

def test_credential_crud():
    db = get_db(":memory:")
    # 测试增删改查
```

### 2. 集成测试

```bash
# 测试API是否正常工作
sh ./test_api.sh

# 检查数据库是否正确初始化
python -c "from src.db import get_db; db = get_db(); print(db.list_providers())"

# 测试模型创建
python -c "from src.llm import create_model_auto; m = create_model_auto('gpt-4o-mini'); print(m)"
```

---

## 🚀 后续优化计划

### 短期（1-2周）

1. **添加测试用例**
   - LLM 模块单元测试
   - 数据库模块单元测试
   - 集成测试

2. **凭证加密**
   - 使用 Fernet 加密存储 API Key
   - 提供加密解密工具

3. **Web 管理界面**
   - 可视化配置供应商和凭证
   - 实时查看模型使用统计

### 中期（1个月）

4. **性能优化**
   - 添加 Redis 缓存层
   - 优化数据库查询
   - 模型实例池管理

5. **成本分析**
   - 基于 usage_logs 生成成本报告
   - 按用户/节点/模型统计费用
   - 预算告警

6. **高级路由**
   - 基于用户类型选择模型
   - 基于时间段选择模型
   - 负载均衡和降级策略

### 长期（3个月）

7. **多租户支持**
   - 租户级凭证隔离
   - 租户级配额管理

8. **模型评估**
   - A/B 测试框架
   - 模型效果评估
   - 自动优化模型选择

---

## 📝 总结

### 解决的问题

✅ **模型配置灵活性** - 支持每个节点使用不同模型
✅ **多供应商支持** - 支持 8+ 个 LLM 供应商
✅ **凭证管理** - 统一管理多套 API 凭证
✅ **代码复用** - 消除重复的模型创建代码
✅ **可维护性** - 清晰的模块划分，易于扩展
✅ **使用统计** - 自动记录 token 使用量
✅ **向后兼容** - 现有代码无需修改

### 架构优势

1. **解耦** - LLM 管理与业务逻辑分离
2. **扩展性** - 新增供应商只需配置，无需改代码
3. **可配置** - 数据库驱动，支持热更新
4. **可观测** - 完整的使用日志和统计
5. **可测试** - 模块化设计，易于编写测试

### 迁移成本

- **零迁移成本** - 现有代码无需修改即可运行
- **渐进式采用** - 可以逐步迁移到新架构
- **学习成本低** - API 设计简洁直观

---

**Happy Coding! 🎉**
