import streamlit as st
import os
import time
from langchain_core.messages import HumanMessage, AIMessage
import re
import streamlit.components.v1 as components

# =============================================================
# 🔥 核心修复：可靠的 Mermaid 渲染函数
# =============================================================
def render_mermaid_html(mermaid_code, height=300):
    """
    使用 CDN 加载 Mermaid 库并渲染图表。
    """
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
    """
    Python 控制的逐步生成动画
    """
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
    
    # 创建一个空的占位符，用于不断更新图表
    placeholder = container.empty()
    
    # 逐步构建 Mermaid 代码
    for i in range(1, len(STEPS) + 1):
        current_steps = STEPS[:i]
        
        # 构建 Mermaid 语法
        lines = ["flowchart LR"]
        
        # 定义子图
        lines.append(f'    subgraph {TITLE} ["🚀 {TITLE}"]')
        lines.append("    direction LR")
        
        # 定义节点
        for idx, s in enumerate(current_steps):
            node_id = f"Node{idx}"
            # 如果是当前最新的一步，通过样式高亮显示
            if idx == i - 1:
                lines.append(f'        {node_id}["✨ {s}"]:::active')
            else:
                lines.append(f'        {node_id}["{s}"]')
        
        # 定义连接线
        for idx in range(len(current_steps) - 1):
            lines.append(f"        Node{idx} --> Node{idx+1}")
            
        lines.append("    end")
        
        # 定义样式类
        lines.append("    classDef active fill:#f96,stroke:#333,stroke-width:2px,color:white;")
        
        final_code = "\n".join(lines)
        
        # 在占位符中渲染
        with placeholder:
            render_mermaid_html(final_code, height=250)
            
        # 暂停一小会，形成动画效果
        time.sleep(interval)

# =============================================================
# 🔥 工具：渲染节点信息 (保持不变)
# =============================================================
def render_step_details(container, value, node_name):
    container.markdown(f"#### ⚙️ 正在执行节点: `{node_name}`")

    # 显示记忆
    if isinstance(value, dict) and "memory" in value and value["memory"]:
        with container.expander("🧠 记忆更新", expanded=False):
            st.json(value["memory"])

    # 显示消息
    if isinstance(value, dict) and "messages" in value and value["messages"]:
        last_msg = value["messages"][-1]
        content = getattr(last_msg, "content", str(last_msg))

        if isinstance(last_msg, AIMessage):
            container.info(f"🤖 **节点输出**:\n{content}")
        else:
            container.write(f"👤 **输入**:\n{content}")

    # 显示 PRINT 输出
    if isinstance(value, dict) and value.get("stdout"):
        container.code(value["stdout"])

    container.divider()

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

# =============================================================
# 侧边栏 - 文件上传与记忆注入
# =============================================================
# 1. 定义场景映射 (UI显示名称 -> 后端提示词)
ALIGNMENT_TYPES = {
    "自动/智能识别": "auto",
    "内检测对齐": "internal",
    "外检测对齐": "external",
    "建设期对齐": "construction"
}

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

    # ========== 清洗 ==========
    with tab_clean:
        st.caption("上传单个文件进行格式清洗")
        clean_file = st.file_uploader("选择文件", type=["xlsx", "xls"], key="clean_file")
        if clean_file:
            path = os.path.join(UPLOAD_DIR, clean_file.name)
            with open(path, "wb") as f:
                f.write(clean_file.getbuffer())
            update_agent_memory({"cleaning_target": clean_file.name})
            st.success(f"已就绪：{clean_file.name}")

    # ========== 对齐 ==========
    with tab_align:
        st.caption("上传两个文件进行缺陷与焊缝锚点对齐")

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
# 主聊天区域
# =============================================================

for msg in st.session_state.messages:
    with st.chat_message("user" if isinstance(msg, HumanMessage) else "assistant"):
        st.write(msg.content)


# =============================================================
# 处理用户输入
# =============================================================

if user_input := st.chat_input("请输入你的指令…"):

    st.chat_message("user").write(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            inputs = {"messages": [HumanMessage(content=user_input)]}

            # ----------- 判断是哪种流程并播放动画 ------------
            mode = None
            if "清洗" in user_input:
                mode = "clean"
            if "对齐" in user_input:
                mode = "align"

            # 1. 播放思维导图动画（在处理开始前）
            if mode:
                with st.expander("📊 智能体思维规划（动态）", expanded=True):
                    render_flowchart_stepwise(st, mode)
            
            # 2. LangGraph 流式处理
            with st.status("🤖 AI 正在执行任务...", expanded=True) as status_box:
                
                # 运行 Graph
                events = st.session_state.graph.stream(inputs, config=config)

                for event in events:
                    for node_name, value in event.items():

                        if value is None:
                            continue

                        render_step_details(status_box, value, node_name)

                        if isinstance(value, dict) and "messages" in value and value["messages"]:
                            last_msg = value["messages"][-1]
                            if isinstance(last_msg, AIMessage):
                                full_response = last_msg.content
                                message_placeholder.markdown(full_response + "▌")

                status_box.update(label="✅ 处理完成", state="complete", expanded=False)

            # 3. 显示最终结果
            message_placeholder.markdown(full_response)
            st.session_state.messages.append(AIMessage(content=full_response))

            # 4. 检查生成文件
            generated_files = re.findall(r"\[FILE:(.*?)\]", full_response)

            if generated_files:
                st.success("📁 文件已生成，请下载：")
                for filename in generated_files:
                    filepath = os.path.join(GENERATED_DIR, filename)
                    if os.path.exists(filepath):
                        with open(filepath, "rb") as f:
                            st.download_button(
                                label=f"⬇️ 下载 {filename}",
                                data=f.read(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.warning(f"文件不存在：{filename}")

        except Exception as e:
            st.error(f"❌ 运行错误：{e}")
            import traceback
            st.code(traceback.format_exc())