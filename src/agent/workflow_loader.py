# workflow_loader.py - 工作流配置加载器（委托至 config.py）
from typing import Any, Dict

from ..config import (
    load_yaml,
    get_workflow_config,
    get_tools_config,
    reload_configs,
)


def get_main_workflow_config() -> Dict[str, Any]:
    """获取主工作流配置"""
    return get_workflow_config("main")


def get_order_workflow_config() -> Dict[str, Any]:
    """获取订单工作流配置"""
    return get_workflow_config("order")


def get_logistics_workflow_config() -> Dict[str, Any]:
    """获取物流工作流配置"""
    return get_workflow_config("logistics")


def get_tool_names_for_workflow(workflow_name: str) -> list[str]:
    """获取指定工作流可用的工具列表"""
    tools_config = get_tools_config()
    return tools_config.get("tool_groups", {}).get(workflow_name, [])


def find_node_by_id(config: Dict[str, Any], node_id: str) -> Dict[str, Any]:
    """按 ID 查找工作流节点配置，找不到返回空字典"""
    for node in config.get("nodes", []):
        if node.get("id") == node_id:
            return node
    return {}


def reload_config() -> None:
    """清除缓存，重新加载配置"""
    reload_configs()


__all__ = [
    "load_yaml",
    "get_workflow_config",
    "get_tools_config",
    "get_main_workflow_config",
    "get_order_workflow_config",
    "get_logistics_workflow_config",
    "get_tool_names_for_workflow",
    "find_node_by_id",
    "reload_config",
]
