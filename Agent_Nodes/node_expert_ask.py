from langchain_core.messages import AIMessage
from agent_state import AgentState

def node_expert_ask(state: AgentState):
    print("=== 询问是否添加专家反馈 ===")
    
    # 获取刚刚保存的 ID
    rec_id = state.get("current_record_id")
    
    msg = (
        f"✅ 记录已保存 (ID: {rec_id})。\n\n"
        "**是否需要为此条目添加专家修正意见（阈值与原因）？**\n"
        "• 如果需要，请直接输入（例如：“阈值改为0.8，因为噪声太大”）；\n"
        "• 如果不需要，请回复“不用”或“结束”。"
    )
    
    return {"messages": [AIMessage(content=msg)]}