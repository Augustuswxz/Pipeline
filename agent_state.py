from typing import List, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph.message import add_messages

# ========== 1. 定义状态结构 ==========
class AgentState(TypedDict):
    # messages: List[BaseMessage]
    messages: Annotated[List[BaseMessage], add_messages]
    memory: dict                    # <--- 记忆字段