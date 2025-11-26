import streamlit as st
import os
import time
from langchain_core.messages import HumanMessage, AIMessage
import re
import streamlit.components.v1 as components
import sys
import builtins
import io

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