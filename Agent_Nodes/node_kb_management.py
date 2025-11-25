from langchain_core.messages import AIMessage, ToolMessage
# from Tools.KBManager import view_knowledge_base, update_knowledge_base, delete_knowledge_base, add_new_standard_field, delete_standard_field_tool
from LLM.LLM import llm
from node_wrapper import node_wrapper
from Tools.tools_config import kb_tools

llm_with_tools = llm.bind_tools(kb_tools)


@node_wrapper
def node_kb_management(state):
    print("=== ⚙️ 进入知识库管理节点 ===")
    # print(state)
    messages = state["messages"]
    # print("messages为：",messages)
    memory = state.get("memory", {})
    
    # 1. 调用 LLM 决策（它会决定是“查看”还是“修改”）
    response = llm_with_tools.invoke(messages)
    # print("response为：",response)
    # 检查是否有工具调用
    if response.tool_calls:
        print("🔍 检测到工具调用请求：")
        for tool in response.tool_calls:
            tool_name = tool.get("name")
            tool_args = tool.get("args")
            print(f"   🛠️  工具名称: {tool_name}")
            print(f"   📋  参数内容: {tool_args}")
    else:
        print("🗣️  智能体未调用工具，生成了普通回复。")
        
    return {
        "messages": [response],
        "memory": memory
    }
