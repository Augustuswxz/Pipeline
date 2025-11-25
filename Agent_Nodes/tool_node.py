from agent_state import AgentState
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from LLM.LLM import llm
from Tools.add import add
from node_wrapper import node_wrapper

@node_wrapper
def tool_node(state: AgentState):
    print("=== 进入 Tool 节点 ===")

    messages = state["messages"]
    last_msg = messages[-1].content

    if last_msg.startswith("add:"):
        nums = last_msg.replace("add:", "").split(",")

        if len(nums) != 2:
            return {"messages": messages + [AIMessage(content="格式错误。请用 add:x,y")]}

        try:
            a, b = int(nums[0]), int(nums[1])
            result = add.invoke({"a": a, "b": b})  # 用 LangChain Tool 调用
            return {
                "messages": messages + [AIMessage(content=f"{a} + {b} = {result}")],
                "memory": state["memory"]
            }
        except Exception as e:
            return {"messages": messages + [AIMessage(content=str(e))]}

    return state
