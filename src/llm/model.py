# llm/model.py - LLM 模型配置和工厂
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from functools import lru_cache

from langchain_openai import ChatOpenAI
# from langchain_anthropic import ChatAnthropic  # 暂时注释，如需使用再安装

from .provider import Provider
from .credential import Credential, default_credential_manager


@dataclass
class ModelConfig:
    """模型配置"""
    # 基础配置
    model_name: str  # 模型名称，如 "gpt-4o", "glm-4-plus"
    provider: Provider
    credential_name: str = "default"

    # 模型参数
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    # 高级配置
    streaming: bool = False
    timeout: Optional[int] = None
    max_retries: Optional[int] = None

    # 元数据
    display_name: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """设置默认值"""
        if not self.display_name:
            self.display_name = f"{self.provider.value}/{self.model_name}"

    def to_dict(self) -> dict:
        """转换为字典（用于存储到数据库）"""
        return {
            "model_name": self.model_name,
            "provider": self.provider.value,
            "credential_name": self.credential_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "streaming": self.streaming,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "display_name": self.display_name,
            "description": self.description,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> "ModelConfig":
        """从字典创建模型配置"""
        return ModelConfig(
            model_name=data["model_name"],
            provider=Provider(data["provider"]),
            credential_name=data.get("credential_name", "default"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens"),
            top_p=data.get("top_p", 1.0),
            frequency_penalty=data.get("frequency_penalty", 0.0),
            presence_penalty=data.get("presence_penalty", 0.0),
            streaming=data.get("streaming", False),
            timeout=data.get("timeout"),
            max_retries=data.get("max_retries"),
            display_name=data.get("display_name", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )

    @staticmethod
    def from_yaml_config(yaml_config: dict, provider: Provider = Provider.OPENAI) -> "ModelConfig":
        """从 YAML 配置创建模型配置（兼容旧配置）"""
        return ModelConfig(
            model_name=yaml_config.get("model", "gpt-4o-mini"),
            provider=provider,
            temperature=yaml_config.get("temperature", 0.7),
            max_tokens=yaml_config.get("max_tokens"),
        )


class ModelFactory:
    """模型工厂类"""

    def __init__(self, credential_manager=None):
        self.credential_manager = credential_manager or default_credential_manager
        self._model_cache: Dict[str, Any] = {}

    def create_model(self, config: ModelConfig, cache_key: Optional[str] = None) -> Any:
        """
        创建模型实例

        Args:
            config: 模型配置
            cache_key: 缓存键，如果提供则启用缓存复用

        Returns:
            LangChain 模型实例（ChatOpenAI, ChatAnthropic 等）
        """
        # 检查缓存
        if cache_key and cache_key in self._model_cache:
            return self._model_cache[cache_key]

        # 获取凭证
        credential = self.credential_manager.get_credential(config.credential_name)
        if not credential:
            raise ValueError(f"未找到凭证: {config.credential_name}")

        # 根据供应商创建模型
        if config.provider == Provider.ANTHROPIC:
            model = self._create_anthropic_model(config, credential)
        else:
            # OpenAI 及其兼容接口（包括 Zhipu, Moonshot, DeepSeek, Ollama 等）
            model = self._create_openai_compatible_model(config, credential)

        # 缓存模型实例
        if cache_key:
            self._model_cache[cache_key] = model

        return model

    def _create_openai_compatible_model(
        self, config: ModelConfig, credential: Credential
    ) -> ChatOpenAI:
        """创建 OpenAI 兼容的模型"""
        kwargs = {
            "model": config.model_name,
            "temperature": config.temperature,
            "api_key": credential.api_key,
        }

        # Base URL
        if credential.base_url:
            kwargs["base_url"] = credential.base_url

        # 可选参数
        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens
        if config.timeout:
            kwargs["timeout"] = config.timeout
        if config.max_retries:
            kwargs["max_retries"] = config.max_retries

        # 其他参数 - 直接传递而不是放在 model_kwargs 中
        # 避免 LangChain 警告
        kwargs["top_p"] = config.top_p
        kwargs["frequency_penalty"] = config.frequency_penalty
        kwargs["presence_penalty"] = config.presence_penalty

        # Azure 特殊处理
        if config.provider == Provider.AZURE_OPENAI:
            kwargs["azure_deployment"] = credential.deployment_name
            kwargs["api_version"] = credential.api_version
            kwargs["azure_endpoint"] = credential.base_url

        return ChatOpenAI(**kwargs)

    def _create_anthropic_model(
        self, config: ModelConfig, credential: Credential
    ):
        """创建 Anthropic 模型"""
        # 需要安装: pip install langchain-anthropic
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError:
            raise ImportError(
                "需要安装 langchain-anthropic: pip install langchain-anthropic"
            )

        kwargs = {
            "model": config.model_name,
            "temperature": config.temperature,
            "api_key": credential.api_key,
        }

        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens
        if config.timeout:
            kwargs["timeout"] = config.timeout
        if config.max_retries:
            kwargs["max_retries"] = config.max_retries

        return ChatAnthropic(**kwargs)

    def clear_cache(self):
        """清空模型缓存"""
        self._model_cache.clear()

    def get_cached_model(self, cache_key: str) -> Optional[Any]:
        """获取缓存的模型"""
        return self._model_cache.get(cache_key)


# 全局默认模型工厂
default_model_factory = ModelFactory()


# 便捷函数：从 YAML 配置创建模型
def create_model_from_yaml(
    yaml_config: dict,
    provider: Provider = Provider.OPENAI,
    credential_name: str = "default",
    cache_key: Optional[str] = None,
) -> Any:
    """
    从 YAML 配置创建模型（兼容旧配置格式）

    Args:
        yaml_config: YAML 配置字典，如 {"model": "gpt-4o", "temperature": 0.7}
        provider: 供应商
        credential_name: 凭证名称
        cache_key: 缓存键

    Returns:
        LangChain 模型实例
    """
    config = ModelConfig.from_yaml_config(yaml_config, provider)
    config.credential_name = credential_name
    return default_model_factory.create_model(config, cache_key)


# 便捷函数：推断供应商并创建模型
@lru_cache(maxsize=32)
def create_model_auto(
    model_name: str,
    temperature: float = 0.7,
    credential_name: str = "default",
) -> Any:
    """
    自动推断供应商并创建模型

    Args:
        model_name: 模型名称
        temperature: 温度
        credential_name: 凭证名称

    Returns:
        LangChain 模型实例
    """
    # 根据模型名称推断供应商
    provider = _infer_provider_from_model_name(model_name)

    config = ModelConfig(
        model_name=model_name,
        provider=provider,
        temperature=temperature,
        credential_name=credential_name,
    )

    cache_key = f"{model_name}_{temperature}_{credential_name}"
    return default_model_factory.create_model(config, cache_key)


def _infer_provider_from_model_name(model_name: str) -> Provider:
    """根据模型名称推断供应商"""
    model_lower = model_name.lower()

    if model_lower.startswith("gpt-"):
        return Provider.OPENAI
    elif model_lower.startswith("claude-"):
        return Provider.ANTHROPIC
    elif model_lower.startswith("glm-"):
        return Provider.ZHIPU
    elif model_lower.startswith("moonshot-"):
        return Provider.MOONSHOT
    elif model_lower.startswith("deepseek-"):
        return Provider.DEEPSEEK
    elif "kimi" in model_lower:
        return Provider.MOONSHOT
    else:
        return Provider.CUSTOM
