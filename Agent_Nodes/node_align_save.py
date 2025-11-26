from langchain_core.messages import AIMessage
from Tools.align_tools.alignment_memory import AlignmentMemory

def node_align_save(state):
    print("=== 3. 保存结果 ===")

    # test
    # res_msg = "已采用专家方案。记录已更新。"
    # return {"messages": [AIMessage(content=res_msg)]}

    candidates = state["align_candidates"]
    match_found = state["align_match_found"]
    vector = state["align_vector"]
    
    final_result = None
    
    # === 分支逻辑 ===
    if not match_found:
        # 情况1：无匹配，直接用默认
        final_result = candidates["Default"]
        res_msg = f"对齐完成（无历史参考）。结果：{final_result}"
    else:
        # 情况2：有匹配，解析用户刚才的输入
        last_user_msg = state["messages"][-1].content.strip().upper()
        
        if "B" in last_user_msg or "专家" in last_user_msg:
            # final_result = candidates["Expert"]
            final_result = 0.01
            res_msg = "已采用专家方案。记录已更新。"
        else:
            # final_result = candidates["Default"]
            final_result = 0.02
            res_msg = "已采用默认方案。记录已更新。"
            
    # 存入记忆库
    db = AlignmentMemory()
    new_record_id = db.add_record(vector, final_result)
    
    return {
        "messages": [AIMessage(content=res_msg)],
        "current_record_id": new_record_id 
    }