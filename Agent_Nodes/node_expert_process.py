from langchain_core.messages import HumanMessage, AIMessage
from LLM.LLM import llm
from Tools.align_tools.alignment_memory import AlignmentMemory
import json
from agent_state import AgentState

def node_expert_process(state: AgentState):
    print("=== 更新专家反馈到数据库 ===")
    
    user_input = state["messages"][-1].content
    record_id = state.get("current_record_id")
    
    # 1. LLM 提取阈值和原因
    prompt = f"""
    用户希望更新专家反馈。
    用户输入: "{user_input}"
    请提取:
    - expert_val (float类型数字)
    - comment (简短原因字符串)
    
    请返回纯 JSON 格式: {{"expert_val": 0.8, "comment": "原因..."}}
    """
    
    try:
        # 调用 LLM 提取
        response = llm.invoke([HumanMessage(content=prompt)])
        # 简单的清洗逻辑
        json_str = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        
        val = data.get("expert_val")
        comment = data.get("comment", "专家修正")
        
        if val is None:
            raise ValueError("未提取到数值")
            
        # 2. 调用数据库更新接口
        db = AlignmentMemory()
        # ★★★ 这里调用你提供的更新函数 ★★★
        result_msg = db.update_expert_feedback(record_id, expert_val=val, comment=comment)
        
        reply = f"✅ {result_msg} (阈值: {val})。\n还需要继续修改吗？"
        
    except Exception as e:
        reply = f"❌ 更新失败: {str(e)}。请重新描述数值和原因。"

    return {"messages": [AIMessage(content=reply)]}