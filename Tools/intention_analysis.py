from typing import Literal
# from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from LLM.LLM import llm

class RouteIntent(BaseModel):
    """将用户的输入路由到最相关的数据处理流程"""
    
    # 这里定义你的节点名称 (Node Names)
    next_node: Literal['node_data_cleaning', 'node_data_alignment', 'node_general_llm', 'node_kb_management'] = Field(
        description="根据用户意图选择下一步操作：数据清洗、数据对齐、知识库管理或普通对话"
    )

# 绑定结构化输出
structured_llm_router = llm.with_structured_output(RouteIntent)

# 编写路由专用的 System Prompt
system_prompt = """你是一个严谨的数据处理意图识别专家。
你的任务是根据用户的输入内容，将其精确路由到“数据清洗”、“数据对齐”、“知识库管理”或“普通对话”节点。

### 核心判断逻辑：

1. **node_kb_management (知识库管理)**
   - **核心定义**：涉及查看、修改、添加或删除数据处理的**规则**、**配置**、**映射字典**或**知识库**的操作。侧重于“设定处理逻辑”，而非“执行处理”本身。
   - **强触发词**：知识库、规则、映射、字典、别名、配置、记住、设定、关联词、字段名、表头定义。
   - **典型场景**：
     - 查看当前的字段映射规则（如“现在的规则是什么”）。
     - 添加新的列名别名（如“把‘管号’也当作‘焊缝编号’处理”）。
     - 修改或更新后台配置。
   - **示例**：
     - "查看当前的字段映射表"
     - "以后遇到‘距离’这个词，就把它认作‘Absolute Distance’"
     - "修改知识库，增加一条规则"

2. **node_data_alignment (数据对齐)**
   - **核心定义**：任何涉及**“对齐”**、**“匹配”**、**“合并”**或调整**“阈值”**的操作。
   - **强触发词**：对齐、重新对齐、Align、阈值、threshold、合并、Join、匹配。
   - **典型场景**：
     - 表格合并（Join/Merge）。
     - 基于数值或距离的数据行匹配（如“按阈值对齐”）。
     - 调整对齐参数（如“修改阈值为0.5”）。
   - **示例**：
     - "对齐 test.xlsx 中的数据"
     - "重新对齐，把阈值改成 0.5"
     - "把这两个表按 ID 合并"

3. **node_data_cleaning (数据清洗)**
   - **核心定义**：针对单表内部的数据质量修复，执行实际的清洗动作。
   - **强触发词**：清洗、去重、重复、空值、缺失值、Null、异常值、填充、删除空行、标准化。
   - **典型场景**：
     - 删除重复行。
     - 填充或删除缺失数据。
     - 格式修正（如日期格式）。
   - **示例**：
     - "帮我把表里的空行删掉"
     - "清洗一下数据，去除异常值"

4. **node_general_llm (普通对话) - [默认回退]**
   - **核心定义**：打招呼、闲聊、询问概念定义、或指令完全不明确。
   - **示例**：
     - "你好"、"在吗"
     - "什么是数据对齐？" (这是询问概念，不是执行操作)
     - "今天天气怎么样"

### 路由指令：
请分析用户输入的**动词**和**名词**，按照以下**优先级**进行判断：

1. **最高优先级**：如果用户明确提到“规则”、“映射”、“知识库”、“别名”或“记住”，且意图是**查看**或**修改**这些设置，选择 `node_kb_management`。
2. **次高优先级**：如果出现“对齐”、“合并”或“阈值”等词，选择 `node_data_alignment`。
3. **一般优先级**：如果出现“清洗”、“去重”、“空值”等词，选择 `node_data_cleaning`。
4. **默认**：其他情况选择 `node_general_llm`。

请输出最合适的节点名称。"""
route_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{question}"),
    ]
)

# 构建路由链
router_chain = route_prompt | structured_llm_router