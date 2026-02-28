# db/database.py - 数据库管理器
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class DatabaseManager:
    """SQLite 数据库管理器"""

    def __init__(self, db_path: str = "langgraph.db"):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        # 特殊处理内存数据库
        if db_path == ":memory:":
            self.db_path = db_path
            # 内存数据库需要保持连接，否则数据会丢失
            self._conn = sqlite3.connect(db_path)
            self._conn.row_factory = sqlite3.Row
        else:
            self.db_path = Path(db_path)
            self._conn = None
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """确保数据库文件存在并初始化表结构"""
        # 对于内存数据库或新数据库文件，都需要初始化
        if self.db_path == ":memory:":
            self._initialize_schema()
        elif isinstance(self.db_path, Path) and not self.db_path.exists():
            self._initialize_schema()

    def _initialize_schema(self):
        """初始化数据库表结构"""
        # 使用模块路径而不是 __file__，更可靠
        import src.db
        module_dir = Path(src.db.__file__).parent
        schema_path = module_dir / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        # 内存数据库使用共享连接
        if self._conn is not None:
            yield self._conn
        else:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        执行查询并返回结果

        Args:
            query: SQL 查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        执行更新操作并返回受影响的行数

        Args:
            query: SQL 更新语句
            params: 更新参数

        Returns:
            受影响的行数
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """
        执行插入操作并返回新插入行的 ID

        Args:
            query: SQL 插入语句
            params: 插入参数

        Returns:
            新插入行的 ID
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    # Provider 相关操作
    def get_provider_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取供应商"""
        results = self.execute_query(
            "SELECT * FROM providers WHERE name = ? AND is_active = 1", (name,)
        )
        return results[0] if results else None

    def list_providers(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """列出所有供应商"""
        query = "SELECT * FROM providers"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        return self.execute_query(query)

    # Credential 相关操作
    def get_credential_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取凭证"""
        results = self.execute_query(
            "SELECT * FROM credentials WHERE name = ? AND is_active = 1", (name,)
        )
        return results[0] if results else None

    def create_credential(self, credential_data: Dict[str, Any]) -> int:
        """创建凭证"""
        query = """
            INSERT INTO credentials (
                name, provider_id, api_key, base_url, api_version,
                deployment_name, organization, timeout, max_retries,
                description, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            credential_data["name"],
            credential_data["provider_id"],
            credential_data.get("api_key"),
            credential_data.get("base_url"),
            credential_data.get("api_version"),
            credential_data.get("deployment_name"),
            credential_data.get("organization"),
            credential_data.get("timeout", 60),
            credential_data.get("max_retries", 3),
            credential_data.get("description"),
            credential_data.get("is_active", 1),
        )
        return self.execute_insert(query, params)

    # Model 相关操作
    def get_model_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取模型配置"""
        results = self.execute_query(
            """
            SELECT m.*, p.name as provider_name, c.name as credential_name
            FROM models m
            JOIN providers p ON m.provider_id = p.id
            JOIN credentials c ON m.credential_id = c.id
            WHERE m.name = ? AND m.is_active = 1
            """,
            (name,)
        )
        return results[0] if results else None

    def create_model(self, model_data: Dict[str, Any]) -> int:
        """创建模型配置"""
        query = """
            INSERT INTO models (
                name, model_name, provider_id, credential_id, temperature,
                max_tokens, top_p, frequency_penalty, presence_penalty,
                streaming, timeout, max_retries, display_name, description, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            model_data["name"],
            model_data["model_name"],
            model_data["provider_id"],
            model_data["credential_id"],
            model_data.get("temperature", 0.7),
            model_data.get("max_tokens"),
            model_data.get("top_p", 1.0),
            model_data.get("frequency_penalty", 0.0),
            model_data.get("presence_penalty", 0.0),
            model_data.get("streaming", 0),
            model_data.get("timeout"),
            model_data.get("max_retries"),
            model_data.get("display_name"),
            model_data.get("description"),
            model_data.get("is_active", 1),
        )
        return self.execute_insert(query, params)

    # Node 相关操作
    def get_node_model_config(self, workflow_name: str, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点的模型配置"""
        results = self.execute_query(
            """
            SELECT m.*, p.name as provider_name, c.name as credential_name
            FROM node_model_configs nmc
            JOIN workflow_nodes n ON nmc.node_id = n.id
            JOIN models m ON nmc.model_id = m.id
            JOIN providers p ON m.provider_id = p.id
            JOIN credentials c ON m.credential_id = c.id
            WHERE n.workflow_name = ? AND n.node_id = ?
                AND nmc.is_active = 1 AND m.is_active = 1
            ORDER BY nmc.priority DESC
            LIMIT 1
            """,
            (workflow_name, node_id)
        )
        return results[0] if results else None

    def log_model_usage(self, usage_data: Dict[str, Any]) -> int:
        """记录模型使用日志"""
        query = """
            INSERT INTO model_usage_logs (
                model_id, node_id, user_id, session_id,
                input_tokens, output_tokens, total_tokens, duration_ms,
                status, error_message, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            usage_data.get("model_id"),
            usage_data.get("node_id"),
            usage_data.get("user_id"),
            usage_data.get("session_id"),
            usage_data.get("input_tokens", 0),
            usage_data.get("output_tokens", 0),
            usage_data.get("total_tokens", 0),
            usage_data.get("duration_ms"),
            usage_data.get("status", "success"),
            usage_data.get("error_message"),
            usage_data.get("metadata"),
        )
        return self.execute_insert(query, params)


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db(db_path: str = "langgraph.db") -> DatabaseManager:
    """获取数据库管理器单例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
