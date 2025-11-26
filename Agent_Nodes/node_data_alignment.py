from agent_state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from LLM.LLM import llm
from Tools.align_tools.alignment_param_extractor import alignment_param_extractor
# from Tools.align import data_alignment_tool
from Tools.align_tools.align_defect import pipeline_alignment_tool
from node_wrapper import node_wrapper

@node_wrapper
def node_data_alignment(state: AgentState):
    print("=== 🧩 进入数据对齐节点 (Data Alignment) ===")
    
    # 1. 获取用户最后一条消息以及记忆
    messages = state["messages"]
    memory = state.get("memory", {})

    last_msg = messages[-1]
    user_content = last_msg.content
    print(f"   [输入内容]: {user_content}")

    # 2. 调用 LLM 提取参数
    try:
        print("   [正在提取参数...]")
        # invoking the extraction chain
        params = alignment_param_extractor.invoke({"input": user_content})
        
        # extracted_filename = params.filename
        extracted_threshold = params.threshold
        
        # print(f"   ✅ 提取成功 -> 文件名: {extracted_filename}, 阈值: {extracted_threshold}")
        print(f"   ✅ 提取成功 -> 阈值: {extracted_threshold}")

    except Exception as e:
        # 容错处理：如果提取失败（比如用户没说文件名）
        error_msg = f"参数提取失败，请指明文件名和阈值。错误: {str(e)}"
        return {
            "messages": [AIMessage(content=error_msg)],
            "memory": state.get("memory", {})
        }
    
    # -------------------------------------------
    # 2. 上下文记忆逻辑 (Context Logic) ★★★ 核心修改
    # -------------------------------------------
    
    # --- 处理文件名 ---
    # 2. 直接从记忆读取文件 (对应前端 Tab 2)
    file1 = memory.get("align_file1")
    file2 = memory.get("align_file2")
    print(file1)
    print(file2)

    # 3. 校验
    if not file1 or not file2:
        return {
            "messages": [AIMessage(content="⚠️ 请在左侧【数据对齐】标签页上传两个完整的文件。")],
            "memory": memory
        }
    
    try:
        result = pipeline_alignment_tool.invoke({
            "filename1": file1,
            "filename2": file2,
            "threshold": extracted_threshold
        })
        
        # 4. 返回结果
        # 注意：通常 Tool 的输出应该封装在 ToolMessage 中，或者由 LLM 再次总结
        # 这里为了简单，直接由 AIMessage 返回执行结果
        return {
            "messages": [AIMessage(content=result)],
            "memory": state.get("memory", {})
        }
    
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"工具执行出错: {str(e)}")],
            "memory": state.get("memory", {})
        }