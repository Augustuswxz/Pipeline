from agent_state import AgentState
from langchain_core.messages import AIMessage
from Tools.align_tools.alignment_param_extractor import alignment_param_extractor
from Tools.align_tools.alignment_memory import AlignmentMemory

# 引入你所有的具体执行工具
# from Tools.align_tools.align_defect import pipeline_alignment_tool  # 假设这是内检测
from Tools.align_tools.align_defection import step1_analyze_pipeline_data, step2_generate_alignment_report, calculate_confidence_threshold
# from Tools.align import data_alignment_tool            # 假设这是其他
# from Tools.construction import construction_tool     # 假设这是建设期

from node_wrapper import node_wrapper

@node_wrapper
def node_align_process(state: AgentState):
    print("=== 1. 进入对齐计算节点 (Process) ===")

    # 测试
    # msg_content = "计算完成，发现相似历史场景，已生成双重方案。"
    # match_found = True
    # return {
    #     "messages": [AIMessage(content=msg_content)],
    #     "align_match_found": match_found,
    # }
    
    messages = state["messages"]
    memory = state.get("memory", {})
    last_msg_content = messages[-1].content

    # =========================================
    # 1. 准备阶段：提取参数 & 获取文件 & 确定场景
    # =========================================
    
    # A. 提取阈值 (保留你原来的逻辑)
    # extracted_threshold = 0.1 # 默认值
    # try:
    #     params = alignment_param_extractor.invoke({"input": last_msg_content})
    #     if params.threshold:
    #         extracted_threshold = params.threshold
    #         print(f"   [参数提取] 阈值: {extracted_threshold}")
    # except Exception:
    #     print("   [参数提取] 使用默认阈值")

    # B. 获取文件
    file1 = memory.get("align_file1")
    file2 = memory.get("align_file2")
    
    if not file1 or not file2:
        # 如果文件不全，直接报错返回，不走后续流程
        return {
            "messages": [AIMessage(content="⚠️ 缺少文件，请先在【数据对齐】上传两个文件。")],
            # 这里设置一个标记，让 Router 知道流程该结束了，或者在 Edge 处理
            "align_match_found": False, 
            "align_candidates": {}
        }

    # C. 确定场景与工具
    scenario = memory.get("alignment_scenario", "internal") # 默认为内检测
    print(f"   [当前场景] {scenario}")
    
    # 简单的工具映射工厂
    # 实际调用时，你可以根据 scenario 选择不同的 tool
    # target_tool = pipeline_alignment_tool # 默认
    # if scenario == "external":
    #     target_tool = data_alignment_tool
    # elif scenario == "construction":
    #     target_tool = construction_tool

    # =========================================
    # 2. 记忆检索与计算阶段 (RAG + Logic)
    # =========================================

    # D. 生成向量 (这里先用 Mock，后续你接入真实的 embedding)
    # 真实的逻辑可能是：vector = get_file_embedding(file1)
    data, error = step1_analyze_pipeline_data.invoke({"filename1": file1, "filename2": file2}) 
    if error:
        return {
            "messages": [AIMessage(content=error)]
        }
    file_metric = data['metric']
    print("file_metric:",file_metric)
    file_vector = [float(v) for v in file_metric.values()]
    print("file_vector:",file_vector)

    # E. 查库
    db = AlignmentMemory()
    match = db.search_similar(file_vector)
    
    candidates = {}
    match_found = False
    
    # 计算阈值
    calculated_min_confidence = calculate_confidence_threshold.invoke({"density_metrics": file_metric})
    # 设置默认阈值配置
    default_thresholds = {
        'distance': 1.0,
        'clock_position': 45,
        'length': 10,
        'width': 10,
        'depth':2,
    }

    default_result_msg = step2_generate_alignment_report.invoke({
        "context_data": data, 
        "thresholds": default_thresholds,
        "min_confidence": calculated_min_confidence,
        "save_type": "default"
    })

    # --- 情况 1: 跑默认参数 (方案 A) ---
    # res_default = run_alignment(extracted_threshold, "默认方案")
    res_default = default_result_msg
    candidates["Default"] = res_default
    
    # --- 情况 2: 如果命中历史，跑专家参数 (方案 B) ---
    if match:
        print(f"   ✅ 命中历史记录 (ID: {match['id']})")
        match_found = True
        
        # 获取记忆中的专家参数（这里假设 C 字段存的是阈值，或者其他参数）
        # 如果 C 字段是自然语言，你可能需要用 LLM 把它转回参数
        expert_threshold_vector = match['c_value'] 

        expert_thresholds = {
            'distance':       expert_threshold_vector[0],  # 第1个值
            'clock_position': expert_threshold_vector[1],  # 第2个值
            'length':         expert_threshold_vector[2],  # 第3个值
            'width':          expert_threshold_vector[3],  # 第4个值
            'depth':          expert_threshold_vector[4],  # 第5个值
        }

        expert_result_msg = step2_generate_alignment_report.invoke({
            "context_data": data, 
            "thresholds": expert_thresholds,
            "min_confidence": calculated_min_confidence,
            "save_type": "similar_record"
        })
        
        # 容错：如果数据库里存的 c_value 是空的，就还是用默认
        # expert_threshold = expert_val if expert_val else extracted_threshold
        
        # 跑专家方案
        # 注意：这里我们假设专家调整的是“阈值”，如果专家调整的是其他逻辑，
        # 你可能需要给 Tool 传不同的参数
        # res_expert = run_alignment(expert_threshold, "专家方案")
        res_expert = expert_result_msg
        candidates["Expert"] = res_expert
        
        msg_content = "计算完成，发现相似历史场景，已生成双重方案。"
    else:
        print("   ⚪ 无相似历史")
        msg_content = "计算完成 (标准模式)。"

    # =========================================
    # 3. 返回 State (不直接返回最终文本)
    # =========================================
    return {
        "messages": [AIMessage(content=msg_content)],
        "align_vector": file_vector,
        "align_candidates": candidates,
        "align_match_found": match_found,
        "memory": memory, # 保持记忆
        "default_thresholds_vector": default_thresholds,
        "expert_thresholds_vector": expert_thresholds,
        "context_data": data,
        "record_min_confidence": calculated_min_confidence
    }