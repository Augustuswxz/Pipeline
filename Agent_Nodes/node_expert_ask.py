from langchain_core.messages import AIMessage
from agent_state import AgentState

import re
from langchain_core.messages import AIMessage

def node_expert_ask(state: AgentState):
    print("=== 询问是否添加专家反馈 ===")
    
    # 1. 获取基础信息
    rec_id = state.get("current_record_id")
    messages = state.get("messages", [])
    
    # 2. 检测上一条消息中是否有 [FILE:...] 标记
    file_tag = ""
    last_content = messages[-1].content if messages else ""
    
    # 使用正则提取 [FILE:路径]
    # match 模式解释: 寻找 [FILE: 开头，直到遇到第一个 ] 结尾的内容
    match = re.search(r"(\[FILE:.*?\])", last_content)
    if match:
        file_tag = match.group(1)
        print(f"DEBUG: 检测到上一轮生成了文件: {file_tag}")

    # 3. 根据是否检测到文件，动态调整提示语
    if file_tag:
        # === 场景 A: 刚刚经历过 expert_process (有文件生成) ===
        # 我们把文件链接放在最前面，确保用户能看到按钮，
        # 并且文案改为“继续修改”的语气。
        msg = (
            f"{file_tag}\n\n"  # <--- 关键：把文件链接重新输出一遍
            f"✅ 专家修正已应用 (ID: {rec_id})。\n"
            "**是否还需要继续修改？**\n"
            "• 若需调整：请直接输入新的阈值/原因；\n"
            "• 若已满意：请回复“不用”或“结束”。"
        )
    else:
        # === 场景 B: 刚刚经历过 save_node (第一次进来，无文件) ===
        msg = (
            f"✅ 记录已保存 (ID: {rec_id})。\n\n"
            "**是否需要为此条目添加专家修正意见（阈值与原因）？**\n"
            "• 如果需要，请按以下格式输入：\n"
            "  \"阈值改为[距离, 时钟方位, 长度, 宽度, 深度]，因为...\"\n"
            "  例如：\"阈值改为[1.3, 48, 13, 13, 5]，因为噪声太大\"\n"
            "• 如果不需要，请回复\"不用\"或\"结束\"。"
        )
    
    return {"messages": [AIMessage(content=msg)]}