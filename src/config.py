# config.py - 配置加载统一入口
import os
import yaml
from pathlib import Path
from typing import Any, Dict
from functools import lru_cache
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent          # src/
PROJECT_DIR = BASE_DIR.parent             # 项目根目录
CONFIG_DIR = PROJECT_DIR / "configs"
WORKFLOW_CONFIG_DIR = CONFIG_DIR / "workflows"

load_dotenv(override=True)


class Config:
    """全局配置类"""

    @property
    def openai_api_key(self) -> str:
        return os.environ.get("OPENAI_API_KEY", "")

    @property
    def openai_base_url(self) -> str:
        return os.environ.get("OPENAI_BASE_URL", "")

    @property
    def debug(self) -> bool:
        return os.environ.get("DEBUG", "false").lower() == "true"

    @property
    def log_level(self) -> str:
        return os.environ.get("LOG_LEVEL", "INFO")

    @property
    def host(self) -> str:
        return os.environ.get("HOST", "0.0.0.0")

    @property
    def port(self) -> int:
        return int(os.environ.get("PORT", "8000"))


config = Config()


@lru_cache(maxsize=None)
def load_yaml(filename: str) -> Dict[str, Any]:
    """加载 YAML 配置文件（带全量缓存）"""
    config_path = WORKFLOW_CONFIG_DIR / filename
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_workflow_config(workflow_name: str) -> Dict[str, Any]:
    """根据工作流名称获取配置"""
    workflow_map = {
        "main": "main_workflow.yaml",
        "order": "order_workflow.yaml",
        "logistics": "logistics_workflow.yaml",
    }
    filename = workflow_map.get(workflow_name)
    if not filename:
        raise ValueError(f"未知的工作流: {workflow_name}")
    return load_yaml(filename)


def get_tools_config() -> Dict[str, Any]:
    """获取工具配置"""
    return load_yaml("tools.yaml")


def reload_configs() -> None:
    """清除缓存，重新加载所有配置"""
    load_yaml.cache_clear()
