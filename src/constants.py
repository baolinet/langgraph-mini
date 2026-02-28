# constants.py - 项目常量集中管理
from enum import Enum


class IntentType(str, Enum):
    """意图类型枚举"""
    ORDER = "order"
    LOGISTICS = "logistics"
    GENERAL = "general"
    UNKNOWN = "unknown"


class WorkflowName(str, Enum):
    """工作流名称"""
    MAIN = "main"
    ORDER = "order"
    LOGISTICS = "logistics"
    GENERAL = "general"


class HttpHeader:
    """HTTP 请求头常量"""
    DEVICE_ID = "X-Device-ID"
    DEVICE_ID_ALT = "X-DeviceId"
    DEVICE_ID_ALT2 = "Device-ID"
    USER_AGENT = "User-Agent"
    X_FORWARDED_FOR = "X-Forwarded-For"
    X_REAL_IP = "X-Real-IP"


class DefaultConfig:
    """默认配置常量"""
    DEFAULT_MODEL = "glm-4.7"
    DEFAULT_TEMPERATURE = 0.0
    DEFAULT_INTENT_MODEL = "glm-4.7"
    DEFAULT_INTENT_TEMPERATURE = 0.7
    MAX_MESSAGES_HISTORY = 100
    SESSION_EXPIRE_SECONDS = 3600


class ErrorMessage:
    """错误消息常量"""
    AUTH_FAILED = "认证失败，请重新登录"
    INVALID_TOKEN = "无效的访问令牌"
    WORKFLOW_NOT_FOUND = "工作流不存在"
    UNKNOWN_INTENT = "对不起，我还不清楚您的问题该如何解决"
    INTERNAL_ERROR = "服务器内部错误"


class ToolName:
    """工具名称常量"""
    GET_USER_ID = "get_user_id"
    GET_ORDER_BY_USER_ID = "get_order_by_user_id"
    GET_LOGISTICS_BY_ORDER_ID = "get_logistics_by_order_id"
