# auth.py - 用户身份认证模块
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass
class UserIdentity:
    """用户身份信息"""
    user_id: str
    user_name: str
    email: Optional[str] = None
    role: Optional[str] = None
    device_id: Optional[str] = None
    created_at: Optional[datetime] = None

@dataclass  
class AuthContext:
    """认证上下文，包含用户和设备信息"""
    user: UserIdentity
    access_token: str
    device_info: Optional[dict] = None
    metadata: Optional[dict] = None


class TokenValidator:
    """Token 验证器基类"""
    
    def validate(self, token: str) -> Optional[UserIdentity]:
        raise NotImplementedError


class InMemoryTokenValidator(TokenValidator):
    """内存 Token 验证器（测试/演示用）"""
    
    def __init__(self):
        self._token_user_map: dict[str, dict] = {
            "token-alice": {"user_id": "user-001", "user_name": "Alice"},
            "token-bob": {"user_id": "user-002", "user_name": "Bob"},
        }
    
    def validate(self, token: str) -> Optional[UserIdentity]:
        if not token:
            return None
        
        user_data = self._token_user_map.get(token)
        if user_data is None:
            return None
        
        return UserIdentity(
            user_id=user_data["user_id"],
            user_name=user_data["user_name"],
            email=user_data.get("email"),
            role=user_data.get("role"),
        )
    
    def register_token(self, token: str, user_data: dict) -> None:
        """注册新的 token"""
        self._token_user_map[token] = user_data


class DeviceIdentity:
    """设备身份管理"""
    
    @staticmethod
    def get_device_id(headers: dict) -> Optional[str]:
        """从请求头获取设备 ID"""
        # 常见的设备标识头
        device_id = (
            headers.get("X-Device-ID") or 
            headers.get("X-DeviceId") or
            headers.get("Device-ID")
        )
        return device_id
    
    @staticmethod
    def generate_device_fingerprint(user_agent: str, ip: str) -> str:
        """生成设备指纹"""
        raw = f"{user_agent}:{ip}"
        return hashlib.md5(raw.encode()).hexdigest()


# 默认验证器实例
default_validator = InMemoryTokenValidator()


def resolve_user_by_token(access_token: str) -> Optional[dict]:
    """
    根据 access_token 解析用户身份（兼容旧接口）
    返回 {user_id, user_name}，无效则返回 None
    """
    identity = default_validator.validate(access_token)
    if identity is None:
        return None
    
    return {
        "user_id": identity.user_id,
        "user_name": identity.user_name,
    }


def get_auth_context(access_token: str, headers: Optional[dict] = None) -> Optional[AuthContext]:
    """
    获取完整认证上下文
    """
    identity = default_validator.validate(access_token)
    if identity is None:
        return None
    
    device_info = None
    if headers:
        device_id = DeviceIdentity.get_device_id(headers)
        if device_id:
            device_info = {"device_id": device_id}
    
    return AuthContext(
        user=identity,
        access_token=access_token,
        device_info=device_info,
    )
