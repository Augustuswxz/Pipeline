from agent_state import AgentState
from langchain_core.messages import AIMessage
from Tools.align_tools.alignment_param_extractor import alignment_param_extractor
from Tools.align_tools.alignment_memory import AlignmentMemory

# 引入你所有的具体执行工具
from Tools.align_tools.align_defect import pipeline_alignment_tool  # 假设这是内检测
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
    target_tool = pipeline_alignment_tool # 默认
    # if scenario == "external":
    #     target_tool = data_alignment_tool
    # elif scenario == "construction":
    #     target_tool = construction_tool

    # =========================================
    # 2. 记忆检索与计算阶段 (RAG + Logic)
    # =========================================

    # D. 生成向量 (这里先用 Mock，后续你接入真实的 embedding)
    # 真实的逻辑可能是：vector = get_file_embedding(file1)
    current_vector = [0.1, 0.2, 0.3] 

    # E. 查库
    db = AlignmentMemory()
    match = db.search_similar(current_vector)
    
    candidates = {}
    match_found = False
    
    # 定义一个内部函数来跑工具，避免代码重复
    def run_alignment(thresh, desc):
        print(f"   🏃 正在执行: {desc} (阈值={thresh})...")
        try:
            # 调用你的 LangChain Tool
            return target_tool.invoke({
                "filename1": file1,
                "filename2": file2,
                "threshold": thresh
            })
        except Exception as e:
            return f"执行出错: {str(e)}"

    # --- 情况 1: 跑默认参数 (方案 A) ---
    # res_default = run_alignment(extracted_threshold, "默认方案")
    res_default = "Default res"
    candidates["Default"] = res_default
    
    # --- 情况 2: 如果命中历史，跑专家参数 (方案 B) ---
    if match:
        print(f"   ✅ 命中历史记录 (ID: {match['id']})")
        match_found = True
        
        # 获取记忆中的专家参数（这里假设 C 字段存的是阈值，或者其他参数）
        # 如果 C 字段是自然语言，你可能需要用 LLM 把它转回参数
        expert_val = match['c_value'] 
        
        # 容错：如果数据库里存的 c_value 是空的，就还是用默认
        # expert_threshold = expert_val if expert_val else extracted_threshold
        
        # 跑专家方案
        # 注意：这里我们假设专家调整的是“阈值”，如果专家调整的是其他逻辑，
        # 你可能需要给 Tool 传不同的参数
        # res_expert = run_alignment(expert_threshold, "专家方案")
        res_expert = "Expert"
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
        "align_vector": current_vector,
        "align_candidates": candidates,
        "align_match_found": match_found,
        "memory": memory # 保持记忆
    }