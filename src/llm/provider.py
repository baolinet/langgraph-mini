# llm/provider.py - LLM 供应商管理
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class Provider(str, Enum):
    """LLM 供应商枚举"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"  # 智谱 AI (GLM 系列)
    MOONSHOT = "moonshot"  # 月之暗面 (Kimi)
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"  # 本地模型
    CUSTOM = "custom"  # 自定义兼容 OpenAI API 的服务


@dataclass
class ProviderConfig:
    """供应商配置"""
    provider: Provider
    display_name: str
    base_url_required: bool = True
    api_key_required: bool = True
    supports_streaming: bool = True
    default_base_url: Optional[str] = None

    # 特定供应商的额外配置
    requires_api_version: bool = False  # Azure 需要
    requires_deployment_name: bool = False  # Azure 需要

    def __post_init__(self):
        """设置默认值"""
        if self.default_base_url is None:
            self.default_base_url = PROVIDER_DEFAULTS.get(self.provider, {}).get("base_url")


# 供应商默认配置
PROVIDER_DEFAULTS = {
    Provider.OPENAI: {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
    },
    Provider.AZURE_OPENAI: {
        "base_url": None,  # 用户必须提供
        "models": ["gpt-4", "gpt-35-turbo"],
    },
    Provider.ANTHROPIC: {
        "base_url": "https://api.anthropic.com/v1",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
    },
    Provider.ZHIPU: {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4", "glm-4-plus", "glm-4-flash"],
    },
    Provider.MOONSHOT: {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    },
    Provider.DEEPSEEK: {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
    Provider.OLLAMA: {
        "base_url": "http://localhost:11434/v1",
        "models": ["llama2", "mistral", "codellama"],
    },
}


# 预定义的供应商配置
PROVIDER_CONFIGS = {
    Provider.OPENAI: ProviderConfig(
        provider=Provider.OPENAI,
        display_name="OpenAI",
        base_url_required=False,
        default_base_url=PROVIDER_DEFAULTS[Provider.OPENAI]["base_url"],
    ),
    Provider.AZURE_OPENAI: ProviderConfig(
        provider=Provider.AZURE_OPENAI,
        display_name="Azure OpenAI",
        requires_api_version=True,
        requires_deployment_name=True,
    ),
    Provider.ANTHROPIC: ProviderConfig(
        provider=Provider.ANTHROPIC,
        display_name="Anthropic",
        base_url_required=False,
        default_base_url=PROVIDER_DEFAULTS[Provider.ANTHROPIC]["base_url"],
    ),
    Provider.ZHIPU: ProviderConfig(
        provider=Provider.ZHIPU,
        display_name="智谱 AI (GLM)",
        base_url_required=False,
        default_base_url=PROVIDER_DEFAULTS[Provider.ZHIPU]["base_url"],
    ),
    Provider.MOONSHOT: ProviderConfig(
        provider=Provider.MOONSHOT,
        display_name="Moonshot AI (Kimi)",
        base_url_required=False,
        default_base_url=PROVIDER_DEFAULTS[Provider.MOONSHOT]["base_url"],
    ),
    Provider.DEEPSEEK: ProviderConfig(
        provider=Provider.DEEPSEEK,
        display_name="DeepSeek",
        base_url_required=False,
        default_base_url=PROVIDER_DEFAULTS[Provider.DEEPSEEK]["base_url"],
    ),
    Provider.OLLAMA: ProviderConfig(
        provider=Provider.OLLAMA,
        display_name="Ollama (Local)",
        api_key_required=False,
        default_base_url=PROVIDER_DEFAULTS[Provider.OLLAMA]["base_url"],
    ),
    Provider.CUSTOM: ProviderConfig(
        provider=Provider.CUSTOM,
        display_name="Custom (OpenAI Compatible)",
        base_url_required=True,
    ),
}


def get_provider_config(provider: Provider) -> ProviderConfig:
    """获取供应商配置"""
    return PROVIDER_CONFIGS.get(provider, PROVIDER_CONFIGS[Provider.CUSTOM])


def get_available_models(provider: Provider) -> list[str]:
    """获取供应商支持的模型列表"""
    return PROVIDER_DEFAULTS.get(provider, {}).get("models", [])
