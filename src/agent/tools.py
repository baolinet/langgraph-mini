# tools.py - 工具定义
from langchain_core.tools import tool

@tool
def search_web(query: str) -> str:
    """搜索网络信息，返回相关结果"""
    return f"🔍 搜索'{query}'：LangGraph是构建复杂Agent的强大框架"

@tool
def calculator(expression: str) -> str:
    """计算数学表达式，支持+ - * / ()"""
    try:
        result = eval(expression)
        return f"🧮 {expression} = {result}"
    except Exception as e:
        return f"❌ 计算失败: {str(e)}"

tools = [search_web, calculator]
tools_dict = {
    "search_web": search_web,
    "calculator": calculator
}
