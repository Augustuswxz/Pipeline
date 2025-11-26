from agent_state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage
from LLM.LLM import llm
from node_wrapper import node_wrapper

@node_wrapper
def llm_node(state: AgentState):
    print("=== 进入 LLM 节点 ===")

    messages = state["messages"]
    memory = state.get("memory", {})

    # 1. 定义你的背景人设 (System Prompt)
    persona = """你是一个专业的“数据对齐智能体”。
        你的核心职责是协助用户处理工程数据，具体功能包括：
        1. **数据清洗**：检测并修复数据中的空行、异常值，标准化字段名称。
        2. **数据对齐**：根据里程或位置信息，将不同来源的监测数据进行匹配和合并。
        3. **知识库配置**：管理字段映射规则，允许用户通过自然语言修改系统配置。

        请以专业、简洁、乐于助人的语气回答用户问题。如果上一步有工具执行的结果，请根据结果忠实地向用户汇报，叙述结果内容，不要自作主张添加内容, 即使返回的内容很长也要忠实地展示给用户。"""

    # 在系统提示中注入记忆
    # system_msg = HumanMessage(content=f"你记住的用户信息：{memory}")
    system_content = f"{persona}\n\n【当前上下文记忆】\n{memory}"
    system_msg = SystemMessage(content=system_content)

    # LLM 输入
    llm_input = [system_msg] + messages

    print("[LLM 输入] =", llm_input)

    response = llm.invoke(llm_input)
    print("[LLM 输出] =", response)

    # 返回新消息，但 memory 不变
    return {
        "messages": [response],
        "memory": memory
    }