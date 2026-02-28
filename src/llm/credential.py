# llm/credential.py - LLM 凭证管理
import os
from dataclasses import dataclass, field
from typing import Optional, Dict
from .provider import Provider, get_provider_config


@dataclass
class Credential:
    """LLM 凭证"""
    provider: Provider
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # Azure 特定字段
    api_version: Optional[str] = None
    deployment_name: Optional[str] = None

    # 其他可选字段
    organization: Optional[str] = None
    timeout: int = 60
    max_retries: int = 3

    # 元数据
    name: str = "default"
    description: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """验证凭证完整性"""
        provider_config = get_provider_config(self.provider)

        # 验证 API Key
        if provider_config.api_key_required and not self.api_key:
            raise ValueError(f"{self.provider} 需要 API Key")

        # 验证 Base URL
        if provider_config.base_url_required and not self.base_url:
            # 尝试使用默认值
            if provider_config.default_base_url:
                self.base_url = provider_config.default_base_url
            else:
                raise ValueError(f"{self.provider} 需要 Base URL")

        # Azure 特殊验证
        if self.provider == Provider.AZURE_OPENAI:
            if not self.api_version:
                raise ValueError("Azure OpenAI 需要 api_version")
            if not self.deployment_name:
                raise ValueError("Azure OpenAI 需要 deployment_name")

    def to_dict(self) -> dict:
        """转换为字典（用于存储）"""
        return {
            "provider": self.provider.value,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "api_version": self.api_version,
            "deployment_name": self.deployment_name,
            "organization": self.organization,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> "Credential":
        """从字典创建凭证"""
        return Credential(
            provider=Provider(data["provider"]),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            api_version=data.get("api_version"),
            deployment_name=data.get("deployment_name"),
            organization=data.get("organization"),
            timeout=data.get("timeout", 60),
            max_retries=data.get("max_retries", 3),
            name=data.get("name", "default"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )


class CredentialManager:
    """凭证管理器"""

    def __init__(self):
        self._credentials: Dict[str, Credential] = {}
        self._load_from_env()

    def _load_from_env(self):
        """从环境变量加载默认凭证"""
        # OpenAI / OpenAI 兼容服务
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")

        if api_key:
            # 根据 base_url 推断供应商
            provider = self._infer_provider_from_url(base_url)
            try:
                credential = Credential(
                    provider=provider,
                    api_key=api_key,
                    base_url=base_url,
                    name="env_default",
                    description="从环境变量加载",
                )
                self._credentials["default"] = credential
            except ValueError as e:
                # 如果验证失败，跳过
                pass

        # Azure OpenAI
        azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15")
        azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

        if azure_key and azure_endpoint and azure_deployment:
            try:
                credential = Credential(
                    provider=Provider.AZURE_OPENAI,
                    api_key=azure_key,
                    base_url=azure_endpoint,
                    api_version=azure_version,
                    deployment_name=azure_deployment,
                    name="azure_env_default",
                    description="从环境变量加载的 Azure 凭证",
                )
                self._credentials["azure"] = credential
            except ValueError:
                pass

    def _infer_provider_from_url(self, base_url: Optional[str]) -> Provider:
        """根据 URL 推断供应商"""
        if not base_url:
            return Provider.OPENAI

        base_url = base_url.lower()
        if "azure" in base_url:
            return Provider.AZURE_OPENAI
        elif "moonshot" in base_url or "kimi" in base_url:
            return Provider.MOONSHOT
        elif "bigmodel" in base_url or "zhipu" in base_url:
            return Provider.ZHIPU
        elif "deepseek" in base_url:
            return Provider.DEEPSEEK
        elif "anthropic" in base_url:
            return Provider.ANTHROPIC
        elif "localhost" in base_url or "127.0.0.1" in base_url:
            return Provider.OLLAMA
        else:
            return Provider.CUSTOM

    def add_credential(self, name: str, credential: Credential):
        """添加凭证"""
        self._credentials[name] = credential

    def get_credential(self, name: str = "default") -> Optional[Credential]:
        """获取凭证"""
        return self._credentials.get(name)

    def remove_credential(self, name: str) -> bool:
        """删除凭证"""
        if name in self._credentials:
            del self._credentials[name]
            return True
        return False

    def list_credentials(self) -> list[str]:
        """列出所有凭证名称"""
        return list(self._credentials.keys())

    def get_or_create(self, provider: Provider, name: str = "default") -> Credential:
        """获取或创建凭证"""
        credential = self.get_credential(name)
        if credential and credential.provider == provider:
            return credential

        # 尝试从环境变量创建
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")

        if not api_key:
            raise ValueError(f"未找到凭证 '{name}'，且无法从环境变量创建")

        credential = Credential(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            name=name,
        )
        self.add_credential(name, credential)
        return credential


# 全局默认凭证管理器
default_credential_manager = CredentialManager()
