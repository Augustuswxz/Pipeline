from langchain_core.messages import HumanMessage, AIMessage
from LLM.LLM import llm
from Tools.align_tools.alignment_memory import AlignmentMemory
import json
from agent_state import AgentState
from Tools.align_tools.align_defection import step1_analyze_pipeline_data, step2_generate_alignment_report

def node_expert_process(state: AgentState):
    print("=== 更新专家反馈到数据库 ===")
    
    user_input = state["messages"][-1].content
    record_id = state.get("current_record_id")
    
    # 1. LLM 提取阈值和原因
    prompt = f"""
    用户正在提交专家修改建议，其中包含一组新的阈值向量（通常是5个数值）和修改原因。
    用户输入: "{user_input}"
    
    请仔细提取以下信息：
    - expert_val: 提取新的阈值数组 (格式为浮点数列表 List[float])
    - comment: 提取修改原因 (简短字符串)
    
    请务必仅返回纯 JSON 格式，不要包含 Markdown 标记：
    {{"expert_val": [1.0, 45.0, 10.0, 10.0, 2.0], "comment": "这里是提取出的修改原因..."}}
    """
    
    try:
        # 调用 LLM 提取
        response = llm.invoke([HumanMessage(content=prompt)])
        # 简单的清洗逻辑
        json_str = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(json_str)
        
        new_expert_thresholds = data.get("expert_val")
        comment = data.get("comment", "专家修正")
        
        if new_expert_thresholds is None:
            raise ValueError("未提取到数值")
            
        print("新阈值设置为：",new_expert_thresholds)

        # 重新生成文件
        memory = state.get("memory", {})
        calculated_min_confidence = state["record_min_confidence"]
        file1 = memory.get("align_file1")
        file2 = memory.get("align_file2")
        res_data, error = step1_analyze_pipeline_data.invoke({"filename1": file1, "filename2": file2})
        if error:
            print(error)
        expert_thresholds = {
            'distance':       new_expert_thresholds[0],  # 第1个值
            'clock_position': new_expert_thresholds[1],  # 第2个值
            'length':         new_expert_thresholds[2],  # 第3个值
            'width':          new_expert_thresholds[3],  # 第4个值
            'depth':          new_expert_thresholds[4],  # 第5个值
        }
        modified_result_msg = step2_generate_alignment_report.invoke({
            "context_data": res_data, 
            "thresholds": expert_thresholds,
            "min_confidence": calculated_min_confidence,
            "save_type": "expert_modified"
        })
        # 2. 调用数据库更新接口
        db = AlignmentMemory()
        # ★★★ 这里调用你提供的更新函数 ★★★
        result_msg = db.update_expert_feedback(record_id, expert_val=new_expert_thresholds, comment=comment)
        
        reply = f"""✅ {modified_result_msg}
                    {result_msg} (阈值: {new_expert_thresholds})。
                    还需要继续修改吗？"""
        
    except Exception as e:
        reply = f"❌ 更新失败: {str(e)}。请重新描述数值和原因。"

    return {"messages": [AIMessage(content=reply)]}