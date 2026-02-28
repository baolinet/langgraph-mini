# logistics_graph.py - 物流处理 workflow
from .tools import tools_logistics
from .graph_factory import build_tool_agent_graph
from .workflow_loader import get_logistics_workflow_config

logistics_graph = build_tool_agent_graph(
    workflow_config=get_logistics_workflow_config(),
    tools=tools_logistics,
    use_checkpointer=True,
)
