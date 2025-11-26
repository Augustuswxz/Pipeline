from typing import List, Annotated, Optional
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph.message import add_messages

# ========== 1. 定义状态结构 ==========
class AgentState(TypedDict):
    # messages: List[BaseMessage]
    messages: Annotated[List[BaseMessage], add_messages]
    memory: dict                    # <--- 记忆字段
    align_vector: List[float]       # 新增 对齐中对数据文件分析而得的特征向量
    align_candidates: dict          # 新增 对齐时提供的候选方案，供用户选择
    align_match_found: bool         # 新增 对齐时从对齐记忆库检索是否有特征向量接近的记录
    current_record_id: Optional[str] # 新增 当前存储进对齐记忆库记录的id