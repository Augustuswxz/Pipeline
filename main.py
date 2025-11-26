import streamlit as st
import os
import time
from langchain_core.messages import HumanMessage, AIMessage
import re
import streamlit.components.v1 as components
import sys
import builtins
import io
import uuid
from render import AggressivePrintCapture, render_mermaid_html, render_flowchart_stepwise, render_step_details, render_message_content
from graph import build_graph

# =============================================================
# Streamlit 页面设置
# =============================================================
st.set_page_config(page_title="AI 数据处理助手", layout="wide")
st.title("🤖 AI 数据处理助手（LangGraph + Streamlit）")

UPLOAD_DIR = "UploadedFiles"
GENERATED_DIR = "GeneratedFiles"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "user_streamlit_001"

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

# config = {"configurable": {"thread_id": st.session_state.thread_id}}

# 业务场景
ALIGNMENT_TYPES = {
    "自动/智能识别": "auto",
    "内检测对齐": "internal",
    "外检测对齐": "external",
    "建设期对齐": "construction"
}

# =============================================================
# 侧边栏
# =============================================================
with st.sidebar:
    st.header("🛠️ 数据任务面板")
    st.write(f"当前会话: `{st.session_state.thread_id}`")
    
    if st.button("🧹 开启新对话", use_container_width=True):
        # A. 获取旧记忆（保留文件）
        try:
            # 注意：这里要临时构建一个旧的 config 来读取旧记忆
            old_config = {"configurable": {"thread_id": st.session_state.thread_id}}
            current_state = st.session_state.graph.get_state(old_config)
            saved_memory = current_state.values.get("memory", {})
        except:
            saved_memory = {}
            
        # B. 生成新 ID
        new_thread_id = str(uuid.uuid4())[:8]
        st.session_state.thread_id = new_thread_id
        
        # C. 初始化新线程 (关键：写入记忆，但不带任何 next 状态)
        new_config = {"configurable": {"thread_id": new_thread_id}}
        st.session_state.graph.update_state(
            new_config, 
            {"messages": [], "memory": saved_memory} # 仅写入记忆
        )
        
        # D. 清空前端显示
        st.session_state.messages = []
        
        # E. ★★★ 强制立刻重启脚本 ★★★
        # 这确保了下面的代码会使用新的 ID 重新运行
        st.rerun()

    # 记忆更新函数
    def update_agent_memory(new_data_dict):
        # 🔥 修复核心：在函数内部动态构建 config，确保它是最新的且已定义的
        # 依赖 st.session_state.thread_id，这个变量在代码顶部已经初始化了，所以是安全的
        local_config = {"configurable": {"thread_id": st.session_state.thread_id}}

        try:
            current_state = st.session_state.graph.get_state(local_config)
            current_memory = current_state.values.get("memory", {}) if current_state.values else {}
            current_memory.update(new_data_dict)
            
            # 使用 local_config 更新状态
            st.session_state.graph.update_state(local_config, {"memory": current_memory})
            st.toast(f"🧠 记忆已更新: {new_data_dict}")
        except Exception as e:
            st.error(f"记忆同步失败: {e}")

    tab_clean, tab_align = st.tabs(["🧹 数据清洗", "🧩 数据对齐"])

    # 数据清洗栏
    with tab_clean:
        st.caption("上传单个文件进行格式清洗")
        clean_file = st.file_uploader("选择文件", type=["xlsx", "xls"], key="clean_file")
        if clean_file:
            path = os.path.join(UPLOAD_DIR, clean_file.name)
            with open(path, "wb") as f:
                f.write(clean_file.getbuffer())
            update_agent_memory({"cleaning_target": clean_file.name})
            st.success(f"已就绪：{clean_file.name}")

    # 数据对齐栏
    with tab_align:
        st.caption("上传两个文件进行缺陷与焊缝锚点对齐")

        # 选择业务场景
        # 1. 改为下拉框 (Selectbox)
        selected_label = st.selectbox(
            "选择数据场景 (可选):",
            options=list(ALIGNMENT_TYPES.keys()),
            index=0,
            key="scenario_selector" # 加上 key 是个好习惯
        )

        # 2. 获取对应的值 (如 "internal")
        scenario_context = ALIGNMENT_TYPES[selected_label]
        # 3. 【核心步骤】立刻更新记忆
        # 逻辑：如果选的是"自动"，传给后端 None；否则传具体的值
        # 这样后端可以用 if ui_scenario: 来判断是否强制执行
        memory_value = scenario_context if scenario_context != "auto" else None
        # 只要页面刷新（用户做了选择），这里就会执行，将新状态同步给 Agent
        update_agent_memory({"alignment_scenario": memory_value})

        f1 = st.file_uploader("基准文件 File 1", type=["xlsx", "xls"], key="align1")
        if f1:
            path = os.path.join(UPLOAD_DIR, f1.name)
            with open(path, "wb") as f:
                f.write(f1.getbuffer())
            update_agent_memory({"align_file1": f1.name})
            st.info(f"基准文件：{f1.name}")

        f2 = st.file_uploader("目标文件 File 2", type=["xlsx", "xls"], key="align2")
        if f2:
            path = os.path.join(UPLOAD_DIR, f2.name)
            with open(path, "wb") as f:
                f.write(f2.getbuffer())
            update_agent_memory({"align_file2": f2.name})
            st.info(f"目标文件：{f2.name}")


# =============================================================
# 主聊天区域：渲染历史对话
# =============================================================
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
        render_message_content(msg.content, unique_key_prefix=f"history_{i}")

config = {"configurable": {"thread_id": st.session_state.thread_id}}
# =============================================================
# 处理用户输入
# =============================================================
if user_input := st.chat_input("请输入你的指令…"):

    # 1. 显示用户输入
    st.chat_message("user").write(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        llm_response_text = ""
        
        capturer = AggressivePrintCapture()

        try:
            snapshot = st.session_state.graph.get_state(config)
        
            inputs = None
            events = None # 初始化事件生成器

            # B. 检查是否处于“暂停/中断”状态
            is_paused_at_ask_user = snapshot.next and "ask_user" in snapshot.next
            
            if is_paused_at_ask_user:
                # --- 分支 1: 恢复模式 (Resume) ---
                # snapshot.next 不为空，说明上次运行在某个节点停下了（比如 ask_user）
                st.toast("检测到进行中的任务，正在继续...", icon="🔄")
                
                # 1. 将用户的输入（例如 "A" 或 "B"）注入到状态中
                # as_node="ask_user" 表示把这条消息当作是 ask_user 节点接收到的后续输入
                st.session_state.graph.update_state(
                    config, 
                    {"messages": [HumanMessage(content=user_input)]},
                    as_node="ask_user"  # 👈 确保这里跟你的图结构中产生中断的节点名一致
                )
                
                # 2. 继续运行 (传入 None 表示从断点继续)
                # 此时 mode 设为 None 或特定值，避免渲染错误的思维导图
                inputs = None
                mode = None 

            else:
                # --- 分支 2: 新任务模式 (New Run) ---
                # 之前的流程已结束，这是全新的请求
                mode = None
                if "清洗" in user_input: mode = "clean"
                if "对齐" in user_input: mode = "align"
                
                # 1. 构建标准输入
                inputs = {"messages": [HumanMessage(content=user_input)]}
                

            # 2. 思维导图动画
            if mode:
                with st.expander("📊 智能体思维规划（动态）", expanded=True):
                    render_flowchart_stepwise(st, mode)
            
            # 3. 过程日志容器 (位于思维导图下方，最终回答上方)
            log_display_container = st.container()
            
            # 4. 运行 Graph
            with st.status("🤖 AI 正在执行任务...", expanded=True) as status_box:
                
                log_box = st.empty()
                capturer.set_placeholder(log_box)

                with capturer:
                    events = st.session_state.graph.stream(inputs, config=config)

                    for event in events:
                        for node_name, value in event.items():
                            if value is None: continue

                            render_step_details(status_box, value, node_name)

                            if isinstance(value, dict) and "messages" in value and value["messages"]:
                                last_msg = value["messages"][-1]
                                if isinstance(last_msg, AIMessage):
                                    llm_response_text = last_msg.content
                                    message_placeholder.markdown(llm_response_text + "▌")
                
                status_box.update(label="✅ 处理完成", state="complete", expanded=False)

            # ------------------------------------------------------------------
            # 5. 🔥 处理日志输出 (分离渲染并去除重复行)
            # ------------------------------------------------------------------
            captured_text = capturer.get_all_logs()
            log_section_for_history = ""
            
            if captured_text.strip():
                log_lines = captured_text.strip().split('\n')
                
                # 🔥 关键修复：移除最后可能重复的日志行 (例如：对齐完成！结果已保存到...)
                # 检查最后一行是否包含文件路径信息（这是 LangChain 倾向于重复到最终输出中的内容）
                if '对齐完成！结果已保存到:' in log_lines[-1] and len(log_lines) > 1:
                    log_lines.pop()
                    
                captured_text_filtered = '\n'.join(log_lines) + '\n' if log_lines else ''

                # 5a. 渲染到临时容器 (满足在回答上方的要求)
                log_display_container.markdown("---")
                log_display_container.markdown("### 🧾 过程日志 (Process Logs)")
                log_display_container.code(captured_text_filtered, language="text")

                # 5b. 准备历史记录的保存格式 (使用过滤后的日志)
                if captured_text_filtered.strip():
                    log_section_for_history = f"\n\n---\n**🧾 过程日志 (Process Logs):**\n```text\n{captured_text_filtered}\n```"
            
            # 6. 组合最终内容 (LLM文本 + 历史日志)
            full_response_with_logs = llm_response_text + log_section_for_history

            # 清空 streaming placeholder
            message_placeholder.empty()

            # 7. 保存消息到 Session State
            st.session_state.messages.append(AIMessage(content=full_response_with_logs))
            
            # 8. 立即调用自定义渲染函数显示最终结果和按钮
            render_message_content(full_response_with_logs, unique_key_prefix=f"current_{len(st.session_state.messages)}")

        except Exception as e:
            st.error(f"❌ 运行错误：{e}")
            import traceback
            st.code(traceback.format_exc())