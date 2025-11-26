from langchain_core.messages import AIMessage
from langgraph.types import interrupt, Command

def node_align_ask_user(state):
    print("=== 2. 展示选项并暂停 ===")
    candidates = state["align_candidates"]
    
    # 构造展示给用户的消息
    msg = f"""✅ 发现相似历史场景！已为您生成两份对齐结果：
    
    # 1️⃣ **方案 A (默认)**: {candidates['Default']}
    # 2️⃣ **方案 B (历史专家)**: {candidates['Expert']}
    
    请回复 **"A"** 或 **"B"** 进行选择。"""

    # msg = f"""✅ 发现相似历史场景！已为您生成两份对齐结果：

    # 1️⃣ **方案 A (默认)**: 'Default'
    # 2️⃣ **方案 B (历史专家)**: 'Expert'
    
    # 请回复 **"A"** 或 **"B"** 进行选择。"""
    
    return {
        "messages": [AIMessage(content=msg)]
        # 注意：这里不返回其他字段，只发消息
    }