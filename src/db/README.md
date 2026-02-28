# 数据库模块说明

## 概述

本模块提供了 LiteSQL（SQLite）数据库管理功能，用于存储和管理：
- 🏢 LLM 供应商配置
- 🔑 API 凭证
- 🤖 模型配置
- 🔀 工作流节点
- 🔗 节点与模型的映射关系
- 📊 模型使用日志

## 核心特性

### 1. 灵活的模型配置
- 支持多个 LLM 供应商（OpenAI、智谱、Moonshot、DeepSeek 等）
- 每个节点可以配置不同的模型
- 支持模型热切换，无需重启服务

### 2. 安全的凭证管理
- 统一管理 API Key 和 Base URL
- 支持多个凭证配置
- 后续可扩展加密存储

### 3. 使用统计
- 记录每次模型调用的 token 使用量
- 追踪调用时长和状态
- 支持成本分析和性能优化

## 数据库表结构

### 核心表

1. **providers** - 供应商表
   - 存储 LLM 供应商信息（OpenAI、智谱、Moonshot 等）

2. **credentials** - 凭证表
   - 存储 API Key、Base URL 等认证信息
   - 关联到具体供应商

3. **models** - 模型配置表
   - 存储模型参数（model_name, temperature, max_tokens 等）
   - 关联到供应商和凭证

4. **workflow_nodes** - 工作流节点表
   - 存储节点配置（node_id, system_prompt 等）

5. **node_model_configs** - 节点模型映射表
   - 实现"每个节点使用不同模型"的核心功能
   - 支持优先级和条件路由

### 扩展表

6. **model_usage_logs** - 使用日志表
   - 记录每次模型调用的详细信息

7. **tools** - 工具表
   - 存储可用的工具定义

8. **node_tool_mappings** - 节点工具映射表
   - 定义每个节点可用的工具

## 使用示例

### 初始化数据库

```python
from src.db import get_db

# 获取数据库管理器（自动创建表结构）
db = get_db("langgraph.db")
```

### 查询供应商

```python
# 列出所有供应商
providers = db.list_providers()

# 获取特定供应商
zhipu = db.get_provider_by_name("zhipu")
```

### 管理凭证

```python
# 创建凭证
credential_id = db.create_credential({
    "name": "my_openai_key",
    "provider_id": 1,
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "description": "生产环境 OpenAI 凭证"
})

# 查询凭证
cred = db.get_credential_by_name("my_openai_key")
```

### 管理模型配置

```python
# 创建模型配置
model_id = db.create_model({
    "name": "fast_chat_model",
    "model_name": "gpt-4o-mini",
    "provider_id": 1,
    "credential_id": credential_id,
    "temperature": 0.8,
    "max_tokens": 2000,
    "display_name": "快速对话模型",
    "description": "用于日常对话的快速模型"
})

# 查询模型配置
model = db.get_model_by_name("fast_chat_model")
```

### 获取节点模型配置

```python
# 获取特定节点的模型配置
config = db.get_node_model_config("order", "order_agent")
# 返回：{model_name, provider_name, temperature, ...}
```

### 记录使用日志

```python
# 记录模型使用
db.log_model_usage({
    "model_id": 1,
    "user_id": "user-001",
    "session_id": "session-123",
    "input_tokens": 150,
    "output_tokens": 300,
    "total_tokens": 450,
    "duration_ms": 1500,
    "status": "success"
})
```

## 与 LLM 模块集成

数据库模块可以与 `src/llm` 模块无缝集成：

```python
from src.db import get_db
from src.llm import ModelConfig, default_model_factory, Provider, Credential

# 从数据库加载模型配置
db = get_db()
db_config = db.get_model_by_name("order_agent")

# 转换为 ModelConfig
model_config = ModelConfig(
    model_name=db_config["model_name"],
    provider=Provider(db_config["provider_name"]),
    credential_name=db_config["credential_name"],
    temperature=db_config["temperature"],
    max_tokens=db_config["max_tokens"],
)

# 创建模型实例
model = default_model_factory.create_model(model_config)
```

## 迁移和初始化

### 重新初始化数据库

```bash
# 删除旧数据库
rm langgraph.db

# 重新初始化（自动运行）
python -c "from src.db import get_db; get_db()"
```

### 从环境变量导入凭证

```python
from src.db import get_db
import os

db = get_db()

# 从环境变量创建凭证
openai_provider = db.get_provider_by_name("openai")
db.create_credential({
    "name": "env_default",
    "provider_id": openai_provider["id"],
    "api_key": os.getenv("OPENAI_API_KEY"),
    "base_url": os.getenv("OPENAI_BASE_URL"),
    "description": "从环境变量导入"
})
```

## 后续优化计划

1. **凭证加密** - 使用 Fernet 加密存储 API Key
2. **数据迁移工具** - 提供版本管理和迁移脚本
3. **缓存层** - 添加 Redis 缓存提高查询性能
4. **Web 管理界面** - 提供可视化配置管理
5. **成本分析** - 基于使用日志生成成本报告
