-- schema.sql - LiteSQL 数据库表结构设计
-- 用于存储供应商、模型、凭证和节点配置

-- 1. 供应商表
CREATE TABLE IF NOT EXISTS providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,  -- openai, azure_openai, zhipu 等
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    base_url TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入预定义供应商
INSERT OR IGNORE INTO providers (name, display_name, description, base_url) VALUES
('openai', 'OpenAI', 'OpenAI GPT 系列模型', 'https://api.openai.com/v1'),
('zhipu', '智谱 AI', '智谱 GLM 系列模型', 'https://open.bigmodel.cn/api/paas/v4'),
('moonshot', 'Moonshot AI', 'Kimi 系列模型', 'https://api.moonshot.cn/v1'),
('deepseek', 'DeepSeek', 'DeepSeek 系列模型', 'https://api.deepseek.com/v1'),
('ollama', 'Ollama', '本地模型服务', 'http://localhost:11434/v1'),
('azure_openai', 'Azure OpenAI', 'Azure OpenAI 服务', NULL),
('anthropic', 'Anthropic', 'Claude 系列模型', 'https://api.anthropic.com/v1'),
('custom', 'Custom', '自定义 OpenAI 兼容服务', NULL);

-- 2. 凭证表
CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,  -- default, azure_prod, test_key 等
    provider_id INTEGER NOT NULL,
    api_key TEXT,  -- 加密存储（TODO: 需要加密）
    base_url TEXT,

    -- Azure 特定字段
    api_version VARCHAR(50),
    deployment_name VARCHAR(100),

    -- 通用配置
    organization VARCHAR(100),
    timeout INTEGER DEFAULT 60,
    max_retries INTEGER DEFAULT 3,

    -- 元数据
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_credentials_provider ON credentials(provider_id);
CREATE INDEX IF NOT EXISTS idx_credentials_active ON credentials(is_active);

-- 3. 模型配置表
CREATE TABLE IF NOT EXISTS models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,  -- 配置名称，如 "intent_classifier", "order_agent_model"
    model_name VARCHAR(100) NOT NULL,  -- 实际模型名，如 "gpt-4o", "glm-4-plus"
    provider_id INTEGER NOT NULL,
    credential_id INTEGER NOT NULL,

    -- 模型参数
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER,
    top_p REAL DEFAULT 1.0,
    frequency_penalty REAL DEFAULT 0.0,
    presence_penalty REAL DEFAULT 0.0,

    -- 高级配置
    streaming BOOLEAN DEFAULT 0,
    timeout INTEGER,
    max_retries INTEGER,

    -- 元数据
    display_name VARCHAR(200),
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE,
    FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE CASCADE,
    UNIQUE(name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider_id);
CREATE INDEX IF NOT EXISTS idx_models_credential ON models(credential_id);
CREATE INDEX IF NOT EXISTS idx_models_active ON models(is_active);

-- 4. 工作流节点表
CREATE TABLE IF NOT EXISTS workflow_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name VARCHAR(100) NOT NULL,  -- main, order, logistics
    node_id VARCHAR(100) NOT NULL,  -- intent_router, order_agent, logistics_agent
    node_type VARCHAR(50) NOT NULL,  -- intent_router, react_agent, function
    display_name VARCHAR(200),
    description TEXT,
    system_prompt TEXT,

    -- 元数据
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(workflow_name, node_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_nodes_workflow ON workflow_nodes(workflow_name);
CREATE INDEX IF NOT EXISTS idx_nodes_active ON workflow_nodes(is_active);

-- 5. 节点模型配置映射表（核心表：实现每个节点使用不同模型）
CREATE TABLE IF NOT EXISTS node_model_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,

    -- 优先级（同一节点可能配置多个模型，根据优先级选择）
    priority INTEGER DEFAULT 0,

    -- 条件配置（JSON 格式，用于复杂路由策略）
    -- 例如：{"user_type": "premium", "time_range": "peak"}
    conditions TEXT,

    -- 元数据
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (node_id) REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_node_model_node ON node_model_configs(node_id);
CREATE INDEX IF NOT EXISTS idx_node_model_model ON node_model_configs(model_id);
CREATE INDEX IF NOT EXISTS idx_node_model_priority ON node_model_configs(priority DESC);

-- 6. 模型使用日志表（用于统计和分析）
CREATE TABLE IF NOT EXISTS model_usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id INTEGER NOT NULL,
    node_id INTEGER,
    user_id VARCHAR(100),
    session_id VARCHAR(200),

    -- 使用信息
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    duration_ms INTEGER,

    -- 状态
    status VARCHAR(20),  -- success, error, timeout
    error_message TEXT,

    -- 元数据
    metadata TEXT,  -- JSON 格式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES workflow_nodes(id) ON DELETE SET NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_usage_model ON model_usage_logs(model_id);
CREATE INDEX IF NOT EXISTS idx_usage_node ON model_usage_logs(node_id);
CREATE INDEX IF NOT EXISTS idx_usage_user ON model_usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_created ON model_usage_logs(created_at);

-- 7. 工具配置表
CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,

    -- 工具类型
    tool_type VARCHAR(50),  -- function, api, custom

    -- 工具定义（JSON 格式）
    schema TEXT,

    -- 元数据
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. 节点工具映射表
CREATE TABLE IF NOT EXISTS node_tool_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id INTEGER NOT NULL,
    tool_id INTEGER NOT NULL,

    -- 元数据
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (node_id) REFERENCES workflow_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (tool_id) REFERENCES tools(id) ON DELETE CASCADE,
    UNIQUE(node_id, tool_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_node_tool_node ON node_tool_mappings(node_id);
CREATE INDEX IF NOT EXISTS idx_node_tool_tool ON node_tool_mappings(tool_id);

-- 插入示例数据
-- 示例凭证（实际使用时从环境变量加载）
INSERT OR IGNORE INTO credentials (name, provider_id, api_key, base_url, description) VALUES
('default', 1, 'sk-xxx', 'https://api.openai.com/v1', '默认 OpenAI 凭证'),
('zhipu_default', 2, 'zhipu-xxx', 'https://open.bigmodel.cn/api/paas/v4', '默认智谱凭证');

-- 示例模型配置
INSERT OR IGNORE INTO models (name, model_name, provider_id, credential_id, temperature, display_name, description) VALUES
('intent_classifier', 'kimi-k2-thinking', 3, 1, 0.7, '意图分类器', '用于识别用户意图'),
('order_agent', 'glm-4-flash', 2, 2, 0.0, '订单处理 Agent', '处理订单相关查询'),
('logistics_agent', 'glm-4-flash', 2, 2, 0.0, '物流处理 Agent', '处理物流相关查询'),
('general_agent', 'kimi-k2-thinking', 3, 1, 0.7, '通用对话 Agent', '处理通用任务和对话');

-- 示例工作流节点
INSERT OR IGNORE INTO workflow_nodes (workflow_name, node_id, node_type, display_name, description, system_prompt) VALUES
('main', 'intent_router', 'intent_router', '意图路由器', '识别用户意图并路由到相应工作流', ''),
('order', 'order_agent', 'react_agent', '订单处理 Agent', '使用工具处理订单查询', '用户 ID 是 {user_id}。你需要查询用户的订单信息。'),
('logistics', 'logistics_agent', 'react_agent', '物流处理 Agent', '使用工具处理物流查询', '用户 ID 是 {user_id}。你需要查询物流信息。'),
('general', 'general_agent', 'function', '通用对话 Agent', '处理通用任务', '');

-- 示例节点模型映射
INSERT OR IGNORE INTO node_model_configs (node_id, model_id, priority) VALUES
(1, 1, 100),  -- intent_router -> intent_classifier
(2, 2, 100),  -- order_agent -> order_agent
(3, 3, 100),  -- logistics_agent -> logistics_agent
(4, 4, 100);  -- general_agent -> general_agent
