# workflow_loader.py - 工作流配置动态加载器
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from functools import lru_cache

CONFIG_DIR = Path(__file__).parent.parent.parent / "configs" / "workflows"


@lru_cache(maxsize=1)
def load_yaml(filename: str) -> Dict[str, Any]:
    """加载YAML配置文件"""
    config_path = CONFIG_DIR / filename
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_main_workflow_config() -> Dict[str, Any]:
    """获取主工作流配置"""
    return load_yaml("main_workflow.yaml")


def get_order_workflow_config() -> Dict[str, Any]:
    """获取订单工作流配置"""
    return load_yaml("order_workflow.yaml")


def get_logistics_workflow_config() -> Dict[str, Any]:
    """获取物流工作流配置"""
    return load_yaml("logistics_workflow.yaml")


def get_tools_config() -> Dict[str, Any]:
    """获取工具配置"""
    return load_yaml("tools.yaml")


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


def get_tool_names_for_workflow(workflow_name: str) -> list[str]:
    """获取指定工作流可用的工具列表"""
    tools_config = get_tools_config()
    tool_groups = tools_config.get("tool_groups", {})
    return tool_groups.get(workflow_name, [])


def reload_config():
    """清除缓存，重新加载配置"""
    load_yaml.cache_clear()
