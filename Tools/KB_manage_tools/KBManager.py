# Tools/config_tools.py
from langchain.tools import tool
from Tools.KB_manage_tools.mapping_manager import MappingManager
import json
from typing import List, Optional

@tool
def view_knowledge_base():
    """
    查看当前数据清洗的字段映射规则知识库。
    返回：当前的 JSON 配置内容。
    """
    manager = MappingManager()
    # 为了让 AI 读得懂，返回格式化后的字符串
    # return str(manager.load_as_list_format())
    try:
        with open(manager.filepath, 'r', encoding='utf-8') as f:
            # 读取并重新 dump 成字符串，确保中文显示正常（ensure_ascii=False）
            data = json.load(f)
            return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"读取配置失败: {e}"

@tool
def update_knowledge_base(standard_name: str, new_alias: str):
    """
    向知识库添加新的字段别名映射。
    
    Args:
        standard_name: 标准字段名（必须存在于现有配置中，如 '上游环焊缝编号'）。
        new_alias: 需要添加的别名（如 '管号', 'No.'）。
    """
    manager = MappingManager()
    result = manager.add_alias(standard_name, new_alias)
    return result

@tool
def delete_knowledge_base(standard_name: str, alias_to_remove: str):
    """
    从知识库中删除某个字段的别名映射。
    当某个别名导致错误的匹配，或者不再需要时使用。
    
    Args:
        standard_name: 标准字段名称（如 '上游环焊缝编号'）。
        alias_to_remove: 需要移除的旧别名（如 '错误列名'）。
    """
    manager = MappingManager()
    return manager.delete_alias(standard_name, alias_to_remove)

@tool
def add_new_standard_field(standard_name: str, aliases: Optional[List[str]] = None):
    """
    向知识库添加一个新的标准字段类别。
    例如：增加一个全新的 '腐蚀深度' 字段，并关联别名 ['Corrosion Depth', 'Deep']。
    
    Args:
        standard_name: 新的标准字段名称。
        aliases: (可选) 该字段对应的别名列表。如果不提供，默认为空。
    """
    manager = MappingManager()
    return manager.add_standard_field(standard_name, aliases)

@tool
def delete_standard_field_tool(standard_name: str):
    """
    从知识库中彻底删除一个标准字段（及其下属的所有别名）。
    警告：这是一个破坏性操作，会移除整组映射规则。
    
    Args:
        standard_name: 要删除的标准字段名称（如 '绝对距离(m)'）。
    """
    manager = MappingManager()
    return manager.delete_standard_field(standard_name)