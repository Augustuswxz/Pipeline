from Tools.clean_tools.clean import clean_excel_tool
from langchain_core.messages import AIMessage
# 复用之前的提取器，因为它有 filename 字段
from Tools.KB_manage_tools.mapping_manager import MappingManager

def node_data_cleaning(state):
    print("=== 🧹 进入数据清洗节点 (Data Cleaning) ===")
    messages = state["messages"]
    memory = state.get("memory", {})
    last_msg = messages[-1].content

    # 1. 直接从记忆读取 (对应前端 Tab 1)
    target_file = memory.get("cleaning_target")
    
    # 2. 校验
    if not target_file:
        return {
            "messages": [AIMessage(content="⚠️ 请在左侧【数据清洗】标签页上传需要清洗的文件。")],
            "memory": memory
        }

    print(f"   [自动锁定文件] {target_file}")

    # === 新增：加载外部知识库 ===
    manager = MappingManager()
    current_mapping = manager.load_as_list_format()

    # 3. 调用工具
    try:
        # 这里只演示处理单文件，如果用户说"清洗 test1.xlsx 和 test2.xlsx"
        # 你可能需要更复杂的提取器来提取文件列表。
        # 目前简单处理：只传 filename1
        result = clean_excel_tool.invoke({
            "filename1": target_file, 
            "mapping_config": current_mapping
        })
        
        return {
            "messages": [AIMessage(content=result)],
            "memory": memory
        }
    except Exception as e:
        return {
            "messages": [AIMessage(content=f"清洗工具出错: {e}")],
            "memory": memory
        }