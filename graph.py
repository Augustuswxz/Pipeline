from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from agent_state import AgentState
from LLM.LLM import llm
from Tools.add import add
from Tools.intention_analysis import router_chain
from Tools.tools_config import kb_tools
from Agent_Nodes.llm_node import llm_node
from Agent_Nodes.memory_node import memory_node
from Agent_Nodes.tool_node import tool_node
from Agent_Nodes.node_data_cleaning import node_data_cleaning
from Agent_Nodes.node_data_alignment import node_data_alignment
from Agent_Nodes.node_kb_management import node_kb_management
from langgraph.prebuilt import ToolNode, tools_condition

from typing import List
from typing_extensions import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3 # 确保导入了 sqlite3
from node_wrapper import node_wrapper

def route_logic(state: AgentState):
    print("=== AI Semantic Router (智能路由) ===")

    # 1. 获取用户最新消息
    last_msg = state["messages"][-1]
    content = last_msg.content

    # 2. 调用 LLM 进行意图判断
    # router_chain 会返回一个 RouteIntent 对象
    try:
        decision = router_chain.invoke({"question": content})
        next_node = decision.next_node
    except Exception as e:
        print(f"路由判断出错: {e}，回退到普通对话")
        next_node = "node_general_llm"

    print(f"User Input: {content}")
    print(f"Intent Decision: {next_node}")

    # 3. 返回决策结果 (字符串)
    # 这个字符串必须与 graph.add_conditional_edges 中的 key 对应
    return next_node


# 空节点作为入口
def router_entry_node(state: AgentState):
    pass


# ========== 7. 构建 Graph ==========
def build_graph():

    graph = StateGraph(AgentState)

    # 注册节点
    graph.add_node("llm", node_wrapper(llm_node))
    graph.add_node("router", router_entry_node)
    # ★★★ 注册新节点 (注意名字要对应路由表中的 Value) ★★★
    graph.add_node("data_clean", node_wrapper(node_data_cleaning))      
    # 对应 "node_data_cleaning": "data_clean"
    graph.add_node("data_alignment", node_wrapper(node_data_alignment))
    # 对应 "node_data_alignment": "data_alignment"
    graph.add_node("kb_management", node_kb_management)
    # 知识库管理工具
    kb_tool_node = ToolNode(kb_tools)
    graph.add_node("kb_tool_executor", kb_tool_node)

    # 入口节点
    graph.set_entry_point("router")

    # 条件路由
    graph.add_conditional_edges(
        "router",
        route_logic,
        {
            "node_general_llm": "llm",
            "node_data_cleaning": "data_clean",
            "node_data_alignment": "data_alignment",
            "node_kb_management": "kb_management"
        },
    )

    graph.add_conditional_edges(
        "kb_management", 
        tools_condition, 
        {
            "tools": "kb_tool_executor",  # 如果要执行工具，去执行节点
            "__end__": END # 如果只是闲聊，去通用 LLM 回复
        }
    )

    graph.add_edge("llm", END)
    graph.add_edge("data_clean", END)
    graph.add_edge("data_alignment", END)
    graph.add_edge("kb_tool_executor", "kb_management")

    print("=== Graph 构建完成 ===")

    # ★★★★★ 核心：持久化记忆（SQLite）
    # checkpointer = SqliteSaver.from_file("agent_memory.db")
    # checkpointer = SqliteSaver("agent_memory.db")
    conn = sqlite3.connect("agent_memory.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return graph.compile(checkpointer=checkpointer)


# ========== 8. 交互式测试代码 ==========
if __name__ == "__main__":
    graph = build_graph()

    with open("graph.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())

    # 定义一个固定的 thread_id
    # 只要这个 ID 不变，Agent 就会从 sqlite 文件读取历史
    thread_id = "user_test_001"
    config = {"configurable": {"thread_id": thread_id}}

    print(f"🚀 启动 Agent (Thread ID: {thread_id})")
    print("💾 记忆将会保存在 'agent_memory.db' 文件中")
    print("💡 输入 'exit' 或 'q' 退出程序")
    print("-" * 50)

    while True:
        user_input = input("\n👤 User: ").strip()
        if user_input.lower() in ["exit", "quit", "q"]:
            print("👋 再见！")
            break
        
        if not user_input:
            continue

        # 构造输入状态
        # 注意：因为你没有使用 add_messages reducer，LangGraph 默认行为通常是替换。
        # 但是 SqliteSaver 会加载之前的 checkpoint。
        # 为了稳妥，我们这里传单个消息，LangGraph 会在内部合并 State。
        inputs = {"messages": [HumanMessage(content=user_input)]}

        try:
            # 使用 stream 这样可以看到中间过程（比如进入了哪个节点）
            # print("   (处理中...)") 
            final_state = None
            
            for event in graph.stream(inputs, config=config):
                for node_name, value in event.items():
                    # print(f"   -> 经过节点: {node_name}")
                    final_state = value
            
            if final_state:
                # 提取最后一条消息
                last_msg = final_state["messages"][-1]
                print(f"🤖 AI: {last_msg.content}")
                
                # 🔍 显示当前的显式记忆 (Debug用途)
                current_memory = final_state.get("memory", {})
                if current_memory:
                    print(f"   [当前脑中记忆]: {current_memory}")
            
        except Exception as e:
            print(f"💥 发生错误: {e}")
            import traceback
            traceback.print_exc()