from agent_state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from LLM.LLM import llm
from node_wrapper import node_wrapper

@node_wrapper
def memory_node(state: AgentState):
    print("=== 进入 Memory 节点 ===")

    messages = state["messages"]
    memory = state.get("memory", {})

    last_msg = messages[-1].content.strip()

    # 示例：记住我叫小王
    if last_msg.startswith("记住我叫"):
        name = last_msg.replace("记住我叫", "").strip()
        memory["user_name"] = name

        return {
            "messages": messages + [AIMessage(content=f"好的，我会记住你叫 {name}")],
            "memory": memory
        }

    # 示例：记住我的爱好是足球
    if last_msg.startswith("记住我的爱好是"):
        hobby = last_msg.replace("记住我的爱好是", "").strip()
        memory["hobby"] = hobby

        return {
            "messages": messages + [AIMessage(content=f"收到，我会记住你的爱好是 {hobby}")],
            "memory": memory
        }

    # 如果不是可识别的记忆指令
    return {"messages": messages, "memory": memory}