import streamlit as st
import os
import time
from langchain_core.messages import HumanMessage, AIMessage
import re
import streamlit.components.v1 as components
import sys
import builtins
import io

# =============================================================
# 🔥 核心修复：强力 Print 捕获器 (Hook builtins.print)
# =============================================================
class AggressivePrintCapture:
    """
    这是一个强力捕获器。
    它不依赖 sys.stdout 重定向，而是直接 Hook 掉 Python 的 print 函数。
    """
    def __init__(self):
        self.log_buffer = []
        self.original_print = builtins.print
        self.log_placeholder = None

    def set_placeholder(self, placeholder):
        self.log_placeholder = placeholder

    def _hooked_print(self, *args, **kwargs):
        # 1. 构建输出字符串
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        text = sep.join(map(str, args)) + end

        # 2. 🔥 强制写入 VS Code 真实终端 (绕过 Streamlit 封装)
        try:
            sys.__stdout__.write(text)
            sys.__stdout__.flush()
        except Exception:
            pass

        # 3. 记录到内存 buffer
        self.log_buffer.append(text)

        # 4. (可选) 实时显示在网页顶部，产生“刷屏”效果
        if self.log_placeholder:
            # 只显示最近的 5 行，避免太长
            recent_logs = "".join(self.log_buffer[-5:])
            self.log_placeholder.code(recent_logs, language="text")

    def get_all_logs(self):
        return "".join(self.log_buffer)

    def __enter__(self):
        builtins.print = self._hooked_print
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        builtins.print = self.original_print


# =============================================================
# Mermaid 渲染函数
# =============================================================
def render_mermaid_html(mermaid_code, height=300):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    </head>
    <body>
        <div class="mermaid">
            {mermaid_code}
        </div>
        <script>
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose',
            }});
        </script>
    </body>
    </html>
    """
    components.html(html_content, height=height, scrolling=False)

def render_flowchart_stepwise(container, mode: str, interval=0.8):
    clean_steps = [
        "表格结构解析",
        "知识库自动识别",
        "结构模板映射",
        "单位转换及量纲标准化",
        "结构统一及语义统一的标准化数据",
    ]

    align_steps = [
        "标准化数据",
        "业务场景分析",
        "锚点识别",
        "焊缝/三桩度量",
        "锚点对齐",
        "缺陷分析与度量",
        "缺陷对齐",
        "多源合并数据",
    ]

    STEPS = clean_steps if mode == "clean" else align_steps
    TITLE = "清洗流程" if mode == "clean" else "对齐流程"
    
    placeholder = container.empty()
    
    for i in range(1, len(STEPS) + 1):
        current_steps = STEPS[:i]
        lines = ["flowchart LR"]
        lines.append(f'    subgraph {TITLE} ["🚀 {TITLE}"]')
        lines.append("    direction LR")
        
        for idx, s in enumerate(current_steps):
            node_id = f"Node{idx}"
            if idx == i - 1:
                lines.append(f'        {node_id}["✨ {s}"]:::active')
            else:
                lines.append(f'        {node_id}["{s}"]')
        
        for idx in range(len(current_steps) - 1):
            lines.append(f"        Node{idx} --> Node{idx+1}")
            
        lines.append("    end")
        lines.append("    classDef active fill:#f96,stroke:#333,stroke-width:2px,color:white;")
        
        final_code = "\n".join(lines)
        with placeholder:
            render_mermaid_html(final_code, height=250)
        time.sleep(interval)

# =============================================================
# 渲染节点信息
# =============================================================
def render_step_details(container, value, node_name):
    container.markdown(f"#### ⚙️ 正在执行节点: `{node_name}`")

    if isinstance(value, dict) and "memory" in value and value["memory"]:
        with container.expander("🧠 记忆更新", expanded=False):
            st.json(value["memory"])

    if isinstance(value, dict) and "messages" in value and value["messages"]:
        last_msg = value["messages"][-1]
        content = getattr(last_msg, "content", str(last_msg))

        if isinstance(last_msg, AIMessage):
            container.info(f"🤖 **节点输出**:\n{content}")
        else:
            container.write(f"👤 **输入**:\n{content}")
    
    container.divider()

# =============================================================
# 🔥 新增工具函数：渲染消息内容及下载按钮
# =============================================================
def render_message_content(content, unique_key_prefix):
    """
    渲染消息文本，并检测是否有文件下载标记 [FILE:xxx]。
    如果有，则渲染下载按钮。
    """
    st.markdown(content)
    
    # 检测文件标记
    generated_files = re.findall(r"\[FILE:(.*?)\]", content)
    
    if generated_files:
        st.markdown("---") # 分割线
        st.caption("📁 检测到生成文件：")
        
        for idx, filename in enumerate(generated_files):
            filepath = os.path.join("GeneratedFiles", filename)
            
            # 确保每个按钮有唯一的 key，否则 Streamlit 会报错
            btn_key = f"dl_{unique_key_prefix}_{idx}_{filename}"
            
            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    st.download_button(
                        label=f"⬇️ 下载 {filename}",
                        data=f.read(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=btn_key
                    )
            else:
                st.warning(f"⚠️ 文件已过期或不存在：{filename}")

# =============================================================
# 导入图（Graph）
# =============================================================
try:
    from graph import build_graph
except:
    st.error("❌ 找不到 graph.py / build_graph，请检查文件结构")
    st.stop()

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

config = {"configurable": {"thread_id": st.session_state.thread_id}}

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

    def update_agent_memory(new_data_dict):
        try:
            current_state = st.session_state.graph.get_state(config)
            current_memory = current_state.values.get("memory", {}) if current_state.values else {}
            current_memory.update(new_data_dict)
            st.session_state.graph.update_state(config, {"memory": current_memory})
            st.toast(f"🧠 记忆已更新: {new_data_dict}")
        except Exception as e:
            st.error(f"记忆同步失败: {e}")

    tab_clean, tab_align = st.tabs(["🧹 数据清洗", "🧩 数据对齐"])

    with tab_clean:
        st.caption("上传单个文件进行格式清洗")
        clean_file = st.file_uploader("选择文件", type=["xlsx", "xls"], key="clean_file")
        if clean_file:
            path = os.path.join(UPLOAD_DIR, clean_file.name)
            with open(path, "wb") as f:
                f.write(clean_file.getbuffer())
            update_agent_memory({"cleaning_target": clean_file.name})
            st.success(f"已就绪：{clean_file.name}")

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
            inputs = {"messages": [HumanMessage(content=user_input)]}
            mode = None
            if "清洗" in user_input: mode = "clean"
            if "对齐" in user_input: mode = "align"

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