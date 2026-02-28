# exceptions.py - 自定义异常
from typing import Any, Optional


class AppException(Exception):
    """应用基础异常"""

    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Any] = None):
        self.message = message
        self.code = code or "APP_ERROR"
        self.details = details
        super().__init__(self.message)


class AuthException(AppException):
    """认证异常"""

    def __init__(self, message: str = "认证失败", code: str = "AUTH_ERROR", details: Optional[Any] = None):
        super().__init__(message, code, details)


class WorkflowException(AppException):
    """工作流异常"""

    def __init__(self, message: str = "工作流执行失败", code: str = "WORKFLOW_ERROR", details: Optional[Any] = None):
        super().__init__(message, code, details)


class ValidationException(AppException):
    """验证异常"""

    def __init__(self, message: str = "参数验证失败", code: str = "VALIDATION_ERROR", details: Optional[Any] = None):
        super().__init__(message, code, details)


class ConfigException(AppException):
    """配置异常"""

    def __init__(self, message: str = "配置错误", code: str = "CONFIG_ERROR", details: Optional[Any] = None):
        super().__init__(message, code, details)
