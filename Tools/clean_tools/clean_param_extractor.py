from pydantic import BaseModel, Field
from typing import Optional
from langchain_core.prompts import ChatPromptTemplate
from LLM.LLM import llm # 假设 llm 已经定义并导入

# ==========================================
# 1. 定义 Schema (CleaningParams)
# ==========================================

class CleaningParams(BaseModel):
    """提取数据清洗任务所需的文件名参数"""
    
    filename: Optional[str] = Field(
        default=None, 
        description="目标文件名。如果用户没有在输入中明确提及具体的文件名（如 xxx.xlsx），必须返回 null。"
    )

# ==========================================
# 2. 定义 Prompt
# ==========================================

clean_extract_system_prompt = """你是一个精准的文件名提取助手。
你的任务是从用户的输入中提取【目标文件名】。

### ⚠️ 严格约束 (CRITICAL RULES):
1. **关于文件名**: 
   - 只有当用户明确说了文件名（如 "test.xlsx"）时才提取。
   - 如果用户只说了 "重新清洗"、"清洗这个文件" 等但没有提供具体名字，**filename 字段必须为 null**。
   - 绝对禁止编造文件名。

### 示例 (Few-Shot):
- 输入: "清洗 data_v1.xlsx 中的数据"
  输出: {{ "filename": "data_v1.xlsx" }}

- 输入: "帮我重新清洗一下"
  输出: {{ "filename": null }}

- 输入: "清洗 test.xlsx"
  输出: {{ "filename": "test.xlsx" }}
"""

clean_extract_prompt = ChatPromptTemplate.from_messages([
    ("system", clean_extract_system_prompt),
    ("human", "{input}")
])

# ==========================================
# 3. 绑定 (Cleaning Extractor Chain)
# ==========================================

# 确保 llm 支持 structured_output
cleaning_param_extractor = clean_extract_prompt | llm.with_structured_output(CleaningParams)