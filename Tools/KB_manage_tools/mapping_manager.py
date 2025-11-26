import json
import os

class MappingManager:
    def __init__(self, filepath="KnowledgeBase/field_mapping.json"):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            # 初始化默认值（如果文件不存在）
            default_data = [] 
            os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=4)

    def load_as_list_format(self):
        """
        读取 JSON 并转换为清洗工具需要的 list-of-lists 格式：
        [['标准名', '别名1', '别名2'], ...]
        """
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = []
        for item in data:
            # 将 standard 放在 index 0，后面跟 aliases
            row = [item["standard"]] + item["aliases"]
            result.append(row)
        return result

    def add_alias(self, standard_name, new_alias):
        """给某个标准字段增加别名"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated = False
        for item in data:
            if item["standard"] == standard_name:
                if new_alias not in item["aliases"]:
                    item["aliases"].append(new_alias)
                    updated = True
                break
        
        if updated:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return f"成功将 '{new_alias}' 添加到 '{standard_name}' 的映射中。"
        else:
            return f"未找到标准字段 '{standard_name}'。"

    # 这里还可以添加 create_standard_field, delete_alias 等方法
    def delete_alias(self, standard_name, alias_to_remove):
        """从某个标准字段中删除指定的别名"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        standard_found = False
        alias_removed = False

        for item in data:
            if item["standard"] == standard_name:
                standard_found = True
                if alias_to_remove in item["aliases"]:
                    item["aliases"].remove(alias_to_remove)
                    alias_removed = True
                break
        
        if alias_removed:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return f"成功将 '{alias_to_remove}' 从 '{standard_name}' 的映射中移除。"
        elif standard_found:
            return f"在标准字段 '{standard_name}' 中未找到别名 '{alias_to_remove}'。"
        else:
            return f"未找到标准字段 '{standard_name}'。"
        

    def add_standard_field(self, standard_name, aliases=None):
        """添加一个新的标准字段类别"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否已存在
        for item in data:
            if item["standard"] == standard_name:
                return f"标准字段 '{standard_name}' 已存在，无需重复添加。"
        
        # 创建新条目
        new_entry = {
            "standard": standard_name,
            "aliases": aliases if aliases else []
        }
        data.append(new_entry)
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        return f"成功添加新标准字段: '{standard_name}'。"
    

    def delete_standard_field(self, standard_name):
        """删除一个标准字段及其所有别名（整组删除）"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 过滤掉要删除的项
        original_len = len(data)
        new_data = [item for item in data if item["standard"] != standard_name]
        
        if len(new_data) < original_len:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=4)
            return f"成功删除标准字段 '{standard_name}' 及其所有关联别名。"
        else:
            return f"未找到标准字段 '{standard_name}'，无法删除。"
