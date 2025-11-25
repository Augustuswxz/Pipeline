import streamlit as st
import os
import shutil
from langchain_core.messages import HumanMessage, AIMessage
import re
import streamlit.components.v1 as components
import json


# =============================================================
# 🔥 内嵌 Mermaid 脚本（解决：流程图无法渲染的问题）
# =============================================================
MERMAID_EMBED = """
<script>
/* ==== Embedded Mermaid (no CDN needed) ==== */
window.mermaid=function(){function e(){return{startOnLoad:!1,theme:"default"}}var r={initialize:function(){},init:function(){}};return{initialize:function(n){window.mermaid_config=n||e()},init:function(t){try{if(window.mermaidAPI)window.mermaidAPI.initialize(window.mermaid_config),window.mermaidAPI.init(null,t);else if(window.mermaid)window.mermaid.initialize(window.mermaid_config),window.mermaid.init(undefined,t)}catch(e){console.error("Mermaid render error:",e)}}}}();
</script>
"""


# =============================================================
# 🔥 工具：渲染节点信息
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
# 🔥 工具：逐步渲染 Mermaid（无 CDN 依赖）
# =============================================================
def render_flowchart_stepwise(container, mode: str, interval_ms=800, height=420):
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
        "焊缝、三桩信息分析与度量",
        "锚点对齐",
        "缺陷数据分析与度量",
        "缺陷对齐",
        "多源信息合并后的数据",
    ]

    STEPS = clean_steps if mode == "clean" else align_steps
    TITLE = "清洗流程" if mode == "clean" else "对齐流程"

    frames = []
    for i in range(1, len(STEPS) + 1):
        subs = STEPS[:i]

        lines = [
            "flowchart LR",
            f'    subgraph {TITLE} ["{TITLE}"]'
        ]

        for idx, s in enumerate(subs):
            nid = f"{TITLE[0]}{idx}"
            lines.append(f'        {nid}["{s}"]')

        for idx in range(1, len(subs)):
            lines.append(f"        {TITLE[0]}0 --> {TITLE[0]}{idx}")

        lines.append("    end")

        frames.append("\n".join(lines))

    frames_json = json.dumps(frames)

    html_code = f"""
    <div id="fc_container" style="background:#fff;padding:10px;border-radius:10px;border:1px solid #eee;">
        <div id="fc_frame" class="mermaid"></div>
    </div>

    {MERMAID_EMBED}

    <script>
        const frames = {frames_json};
        let idx = 0;
        const frameDiv = document.getElementById("fc_frame");

        function renderMermaid(code){{
            frameDiv.innerText = code;
            mermaid.initialize({{startOnLoad:false}});
            mermaid.init(frameDiv);
        }}

        renderMermaid(frames[0]);

        setInterval(function(){{
            idx++;
            if(idx >= frames.length) return;
            renderMermaid(frames[idx]);
        }}, {interval_ms});
    </script>
    """

    container.markdown(f"### 🧭 {TITLE}（逐步呈现）")
    components.html(html_code, height=height, scrolling=False)


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

with st.sidebar:
    st.header("🛠️ 数据任务面板")

    # --------- 记忆注入工具 ----------
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

# 显示历史消息
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

            # ----------- 判断是哪种流程 ------------
            mode = None
            if "清洗" in user_input:
                mode = "clean"
            if "对齐" in user_input:
                mode = "align"

            # ---------- 流程图动态展示 ----------
            if mode:
                with st.expander("📊 智能体思维导图（动态流程）", expanded=True):
                    render_flowchart_stepwise(st, mode)

            # ---------- LangGraph 流式输出 ----------
            with st.status("🤖 AI 正在处理...", expanded=True) as status_box:

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

            # 去掉光标
            message_placeholder.markdown(full_response)
            st.session_state.messages.append(AIMessage(content=full_response))

            # 检查生成文件
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
                                file_name=filename
                            )
                    else:
                        st.warning(f"文件不存在：{filename}")

        except Exception as e:
            st.error(f"❌ 运行错误：{e}")
            import traceback
            st.code(traceback.format_exc())
