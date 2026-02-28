# order_graph.py - 订单处理 workflow
from .tools import tools_order
from .graph_factory import build_tool_agent_graph
from .workflow_loader import get_order_workflow_config

order_graph = build_tool_agent_graph(
    workflow_config=get_order_workflow_config(),
    tools=tools_order,
    use_checkpointer=True,
)
