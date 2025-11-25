import streamlit as st
import streamlit.components.v1 as components

st.title("Mermaid 流程图测试")

mermaid_code = """
flowchart LR
    A["开始"] --> B["步骤一"]
    B --> C["步骤二"]
    C --> D["结束"]
"""

html = f"""
<div class="mermaid">
{mermaid_code}
</div>

<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>
    mermaid.initialize({{startOnLoad:true}});
</script>
"""

components.html(html, height=400, scrolling=False)
