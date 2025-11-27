from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
# from Tools.KBManager import view_knowledge_base, update_knowledge_base, delete_knowledge_base, add_new_standard_field, delete_standard_field_tool
from LLM.LLM import llm
from node_wrapper import node_wrapper
from Tools.tools_config import kb_tools
import json

llm_with_tools = llm.bind_tools(kb_tools)


@node_wrapper
def node_kb_management(state):
    print("=== ⚙️ 进入知识库管理节点 ===")
    messages = state["messages"]
    memory = state.get("memory", {})

    if messages and isinstance(messages[-1], ToolMessage):
        last_msg = messages[-1]
        
        # 判断是否是查看知识库的工具返回
        if last_msg.name == "view_knowledge_base":
            print("⚡️ 检测到刚执行完查看知识库，跳过 LLM，直接格式化输出结果。")
            
            try:
                # 1. 将字符串反序列化为 Python 列表
                kb_data = json.loads(last_msg.content)
                
                # 2. 格式化逻辑：遍历列表，拼接字符串
                # 假设数据结构是: [{"standard": "A", "aliases": ["a1", "a2"]}, ...]
                formatted_lines = []
                
                # 容错：如果返回的是单个字典，转为列表
                if isinstance(kb_data, dict):
                    kb_data = [kb_data]
                    
                for item in kb_data:
                    standard = item.get("standard", "未知字段")
                    aliases = item.get("aliases", [])
                    
                    # 将别名列表转为字符串 (如果有多个别名，用逗号分隔)
                    if isinstance(aliases, list):
                        alias_str = ", ".join(aliases)
                    else:
                        alias_str = str(aliases)
                    
                    # 按照你的要求拼接： Standard：Alias
                    formatted_lines.append(f"{standard}：{alias_str}")
                
                # 3. 组合最终文本
                result_text = "\n".join(formatted_lines)
                final_content = f"**当前知识库映射规则如下：**\n\n```text\n{result_text}\n```"

            except Exception as e:
                # 如果解析失败（比如返回的不是JSON），降级为直接显示原始内容
                print(f"❌ JSON解析失败: {e}")
                final_content = f"**知识库内容:**\n{last_msg.content}"

            # 直接返回构造好的 AIMessage
            return {
                "messages": [AIMessage(content=final_content)],
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
