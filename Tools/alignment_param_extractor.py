from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from LLM.LLM import llm # 假设你之前的 LLM 实例

# 1. Schema 保持不变
class AlignmentParams(BaseModel):
    """提取数据对齐任务所需的参数"""
    filename: Optional[str] = Field(
        default=None, 
        description="目标文件名。如果用户没有在输入中明确提及具体的文件名，必须返回 null。"
    )
    threshold: Optional[float] = Field(
        default=None, 
        description="误差阈值。如果用户未指定，必须返回 null。"
    )

# 2. 修改 Prompt：所有 JSON 示例的 { } 都要变成 {{ }}
extract_system_prompt = """你是一个精准的参数提取助手。
你的任务是从用户的输入中提取【文件名】和【阈值】。

### ⚠️ 严格约束 (CRITICAL RULES):
1. **关于文件名**: 
   - 只有当用户明确说了文件名（如 "test.xlsx"）时才提取。
   - 如果用户只说了 "重新对齐" 但没说具体名字，**filename 字段必须为 null**。
   - 绝对禁止编造文件名。

2. **关于阈值**:
   - 提取具体的数值。
   - 如果用户没说，**threshold 字段必须为 null**。

### 示例 (Few-Shot):
- 输入: "对齐 data_v1.xlsx，阈值设为 0.3"
  输出: {{ "filename": "data_v1.xlsx", "threshold": 0.3 }}

- 输入: "帮我把阈值改成 0.5"
  输出: {{ "filename": null, "threshold": 0.5 }}

- 输入: "重新对齐一下"
  输出: {{ "filename": null, "threshold": null }}

- 输入: "对齐 test.xlsx"
  输出: {{ "filename": "test.xlsx", "threshold": null }}
"""

# 注意：这里使用了 from_messages，它内部会调用 format，所以上面的 string 必须转义
extract_prompt = ChatPromptTemplate.from_messages([
    ("system", extract_system_prompt),
    ("human", "{input}")
])

# 3. 绑定
alignment_param_extractor = extract_prompt | llm.with_structured_output(AlignmentParams)