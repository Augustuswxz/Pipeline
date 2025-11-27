import os
import openpyxl
from langchain.tools import tool
from typing import Optional

@tool
def clean_excel_tool(filename1: str, mapping_config: list, filename2: Optional[str] = None) -> str:
    """
    清洗 Excel 文件工具。
    功能：
    1. 删除表头之前的空行。
    2. 根据预设字典标准化字段名称（如将 "里程"、"Absolute Distance" 统一修改为 "绝对距离(m)"）。
    
    Args:
        filename1: 第一个 Excel 文件名（位于 UploadedFiles 目录下）。
        mapping_config: 字段映射配置列表，格式为 [['标准名', '别名1'...], ...]
        filename2: (可选) 第二个 Excel 文件名。如果提供，将同时清洗该文件。
        
    Returns:
        str: 执行结果报告，包含输出文件的名称。
    """
    
    # 1. 路径设置
    base_dir = os.getcwd()
    if not os.path.exists(base_dir):
        return f"错误：目录 {base_dir} 不存在。"

    # ================= 内部辅助函数 (Helper Functions) =================
    
    def edit_distance(s1, s2):
        """计算两个字符串的编辑距离"""
        if len(s1) < len(s2):
            return edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def calculate_similarity_score(field_name, keyword_list):
        """
        计算字段名与关键词列表的匹配分数
        返回最高分数和对应的标准名称
        """
        max_score = 0
        best_match = None

        for keyword in keyword_list:
            score = 0

            # 1. 完全匹配最高分
            if field_name.lower() == keyword.lower():
                score = 100
            # 2. 包含关系
            elif keyword.lower() in field_name.lower() or field_name.lower() in keyword.lower():
                # 计算包含比例
                contain_ratio = len(keyword) / len(field_name) if len(field_name) > 0 else 0
                score = 80 + min(20, contain_ratio * 20)  # 基础80分，根据包含比例加分
            # 3. 编辑距离匹配
            else:
                distance = edit_distance(field_name.lower(), keyword.lower())
                max_len = max(len(field_name), len(keyword))
                if max_len > 0:
                    similarity = 1 - distance / max_len
                    score = similarity * 60  # 编辑距离匹配最高60分

            # 更新最高分
            if score > max_score:
                max_score = score
                best_match = keyword_list[0]  # 使用列表的第一个作为标准名称

        return max_score, best_match

    def find_best_standardization(field_name, standardization_dict):
        """
        为字段名找到最佳的标准名称
        返回匹配分数和标准名称
        """
        best_score = 0
        best_standard = None

        for std_list in standardization_dict:
            score, standard_name = calculate_similarity_score(field_name, std_list)
            if score > best_score:
                best_score = score
                best_standard = standard_name

        return best_score, best_standard

    def remove_empty_rows(sheet):
        """删除字段名之前的空行"""
        values = list(sheet['A'])
        for i in range(len(values)):
            row = list(sheet[1])
            count = 0
            for j in row:
                if j.value is None:
                    sheet.delete_rows(idx=1)
                    break
                else:
                    count = count + 1
            if count == len(row):
                break

    def standardize_field_names(sheet, dic):
        """标准化字段名称 - 使用打分机制找到最佳匹配"""
        fields = list(sheet[1])
        dis_loc = 64  # ASCII码中 '@' 的位置，下一个是 'A'

        for field in fields:
            dis_loc = dis_loc + 1
            if field.value is None:
                continue

            field_name = str(field.value).strip()
            best_score, best_standard = find_best_standardization(field_name, dic)

            # 设置匹配阈值，只有足够相似的才进行标准化
            if best_score >= 60:  # 阈值可以根据需要调整
                loc = chr(dis_loc) + '1'
                sheet[loc].value = best_standard
                # print(f"字段标准化: '{field_name}' -> '{best_standard}' (匹配分数: {best_score:.1f})")
            # elif best_score >= 30:  # 中等匹配，可以记录但不修改或根据需要处理
            #     print(f"字段疑似匹配: '{field_name}' -> '{best_standard}' (匹配分数: {best_score:.1f})")

    # ================= 主逻辑 =================

    # 定义要处理的文件列表
    files_to_process = [filename1]
    if filename2:
        files_to_process.append(filename2)
        
    results = []
    # 用于记录生成的输出文件路径，方便返回
    generated_files = []

    # 定义字段名称映射字典 (标准名在 index 0)
    # dic = [
    #     ['绝对距离(m)', '里程', 'Absolute Distance', '环焊缝里程'],
    #     ['相对距离(m)', '距环焊缝距离', 'Relative Distance'],
    #     ['上游环焊缝编号', 'Upstream Girth Weld', 'weld_id', '序号', '管节编号'],
    #     ['深度(%)', '深度', 'peak depth', 'Peak Depth'],
    #     ['长度(mm)', '长度', 'length', 'Length'],
    #     ['宽度(mm)', '宽度', 'width', 'Width'],
    #     ['时钟方位', 'orientation', 'Orientation']
    # ]
    dic = mapping_config 

    if not dic or len(dic) == 0:
        return "警告：未提供字段映射配置，无法执行字段标准化。"

    for fname in files_to_process:
        input_path = os.path.join(base_dir, "UploadedFiles", os.path.basename(fname))
        output_name = f"clean_{os.path.basename(fname)}"
        output_path = os.path.join(base_dir, "GeneratedFiles", output_name)

        if not os.path.exists(input_path):
            results.append(f"❌ 文件不存在: {fname}")
            continue

        try:
            wb = openpyxl.load_workbook(input_path)
            
            # 默认处理 Sheet1，如果没有则处理第一个激活的表
            # if 'Sheet1' in wb.sheetnames:
            #     sheet = wb['Sheet1']
            # else:
            #     sheet = wb.active
            # 总是处理第一个sheet
            sheet = wb.worksheets[0]

            remove_empty_rows(sheet)
            standardize_field_names(sheet, dic)

            wb.save(output_path)
            results.append(f"✅ {fname} 清洗完成 -> 已保存为: {output_name}")
            generated_files.append(output_name)

        except Exception as e:
            results.append(f"❌ 处理 {fname} 时出错: {str(e)}")

    # 返回结果
    # 我们在返回字符串中加入特殊标记 [FILE:xxx]，方便前端提取（这是一个常用的小技巧）
    response_msg = "\n".join(results)
    if generated_files:
        response_msg += "\n\n生成的文件: " + ", ".join([f"[FILE:{f}]" for f in generated_files])
        
    return response_msg