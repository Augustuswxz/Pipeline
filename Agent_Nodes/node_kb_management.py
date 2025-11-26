from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
# from Tools.KBManager import view_knowledge_base, update_knowledge_base, delete_knowledge_base, add_new_standard_field, delete_standard_field_tool
from LLM.LLM import llm
from node_wrapper import node_wrapper
from Tools.tools_config import kb_tools

llm_with_tools = llm.bind_tools(kb_tools)


@node_wrapper
def node_kb_management(state):
    print("=== ⚙️ 进入知识库管理节点 ===")
    messages = state["messages"]
    memory = state.get("memory", {})

    if messages and isinstance(messages[-1], ToolMessage):
        last_msg = messages[-1]
        # print("last_msg:", last_msg)
        if last_msg.name == "view_knowledge_base":
            print("⚡️ 检测到刚执行完查看知识库，跳过 LLM 处理，直接输出结果。")
            
            # 直接将工具的输出包装成 AI 的回复
            # 为了美观，可以加个 Markdown 的 json 包裹（如果不加，就是纯文本）
            tool_output = last_msg.content
            formatted_content = f"**当前知识库完整内容如下：**\n\n```json\n{tool_output}\n```"
            
            return {
                "messages": [AIMessage(content=formatted_content)],
                "memory": memory
            }

    # 1. 调用 LLM
    response = llm_with_tools.invoke(messages)
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
