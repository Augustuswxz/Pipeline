import math
import os
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Optional, Any
import re
from langchain.tools import tool


import math
import os
import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Optional, Any
import re


class WeldAlignment:
    """环焊缝对齐结果的数据结构"""

    def __init__(self):
        self.alignments = []  # 存储对齐对
        self.first_aligned_weld1 = None  # 第一个对齐的文件1环焊缝
        self.first_aligned_weld2 = None  # 第一个对齐的文件2环焊缝
        self.base_distance = 0  # 使用的基础距离
        self.aligned_count = 0  # 对齐的环焊缝对数

    def add_alignment(self, weld1: str = ' ', dist1: float = 0, redis1: float = 0,
                      weld2: str = ' ', dist2: float = 0, redis2: float = 0,
                      confidence: float = 0.0):
        """添加一个对齐对，包含相对距离信息"""
        self.alignments.append({
            'file1_weld': weld1,
            'file1_distance': dist1,
            'file1_redis': redis1,  # 新增相对距离
            'file2_weld': weld2,
            'file2_distance': dist2,
            'file2_redis': redis2,  # 新增相对距离
            'confidence': confidence
        })

        # 记录第一个对齐的环焊缝
        if self.first_aligned_weld1 is None:
            self.first_aligned_weld1 = {
                'weld': weld1,
                'distance': dist1
            }
        if self.first_aligned_weld2 is None:
            self.first_aligned_weld2 = {
                'weld': weld2,
                'distance': dist2
            }

    def get_file2_weld(self, file1_weld: str) -> Optional[str]:
        """根据文件1的环焊缝编号获取对应的文件2环焊缝编号"""
        for alignment in self.alignments:
            if alignment['file1_weld'] == file1_weld:
                return alignment['file2_weld']
        return None

    def get_file1_weld(self, file2_weld: str) -> Optional[str]:
        """根据文件2的环焊缝编号获取对应的文件1环焊缝编号"""
        for alignment in self.alignments:
            if alignment['file2_weld'] == file2_weld:
                return alignment['file1_weld']
        return None

    def get_all_file1_welds(self) -> List[str]:
        """获取所有文件1的环焊缝编号（包括已对齐和未对齐的）"""
        file1_welds = [a['file1_weld'] for a in self.alignments if a['file1_weld'] != ' ']
        return file1_welds

    def get_all_file2_welds(self) -> List[str]:
        """获取所有文件2的环焊缝编号（包括已对齐和未对齐的）"""
        file2_welds = [a['file2_weld'] for a in self.alignments if a['file2_weld'] != ' ']
        return file2_welds

    def get_nearest_aligned_weld1(self, target_distance: float) -> Optional[Dict]:
        """在文件1中查找距离目标位置最近的已对齐环焊缝"""
        if not self.alignments:
            return None

        nearest = None
        min_distance = float('inf')

        for alignment in self.alignments:
            distance_diff = abs(alignment['file1_distance'] - target_distance)
            if distance_diff < min_distance:
                min_distance = distance_diff
                nearest = {
                    'weld': alignment['file1_weld'],
                    'distance': alignment['file1_distance'],
                    'redis': alignment['file1_redis'],  # 新增相对距离
                    'aligned_weld2': alignment['file2_weld'],
                    'aligned_distance2': alignment['file2_distance'],
                    'aligned_redis2': alignment['file2_redis']  # 新增相对距离
                }

        return nearest

    def get_nearest_aligned_weld2(self, target_distance: float) -> Optional[Dict]:
        """在文件2中查找距离目标位置最近的已对齐环焊缝"""
        if not self.alignments:
            return None

        nearest = None
        min_distance = float('inf')

        for alignment in self.alignments:
            distance_diff = abs(alignment['file2_distance'] - target_distance)
            if distance_diff < min_distance:
                min_distance = distance_diff
                nearest = {
                    'weld': alignment['file2_weld'],
                    'distance': alignment['file2_distance'],
                    'redis': alignment['file2_redis'],  # 新增相对距离
                    'aligned_weld1': alignment['file1_weld'],
                    'aligned_distance1': alignment['file1_distance'],
                    'aligned_redis1': alignment['file1_redis']  # 新增相对距离
                }

        return nearest

    def count_aligned_welds(self) -> int:
        """计算对齐的环焊缝对数"""
        count = 0
        for alignment in self.alignments:
            if alignment['file1_weld'] != ' ' and alignment['file2_weld'] != ' ':
                count += 1
        self.aligned_count = count
        return count


def read_weld_data(df):
    """
    从数据框中读取环焊缝数据

    Args:
        df: 包含管线数据的DataFrame

    Returns:
        tuple: (绝对距离列表, 相对距离列表, 焊缝编号列表)
    """
    # 查找必要的列
    abs_distance_col = None
    weld_number_col = None
    weld_type_col = None
    depth_col = None

    for col in df.columns:
        col_str = str(col).lower()
        if '绝对距离' in col_str:
            abs_distance_col = col
        elif '上游环焊缝编号' in col_str:
            weld_number_col = col
        elif '部件/缺陷类型' in col_str:
            weld_type_col = col
        elif '深度' in col_str:
            depth_col = col

    if abs_distance_col is None:
        raise ValueError("未找到绝对距离列")

    # 检查数据框中是否已有"环焊缝"类型
    has_weld_type = False
    if weld_type_col is not None:
        for idx, row in df.iterrows():
            weld_type = row.get(weld_type_col)
            if pd.notna(weld_type) and str(weld_type).strip() == '环焊缝':
                has_weld_type = True
                break

    # 如果没有找到环焊缝类型，则进行自动标记
    if not has_weld_type and weld_type_col is not None:
        print("未找到环焊缝类型，正在自动标记...")
        for idx, row in df.iterrows():
            weld_number = row.get(weld_number_col)
            depth = row.get(depth_col) if depth_col else None

            # 判断条件：上游环焊缝编号不为空且深度为空
            if (pd.notna(weld_number) and
                    str(weld_number).strip() != '' and
                    (depth is None or pd.isna(depth) or str(depth).strip() == '')):
                # 标记为环焊缝
                df.at[idx, weld_type_col] = '环焊缝'

    # 提取环焊缝数据
    weld_data = []
    now_pipe_num = 10

    for idx, row in df.iterrows():
        abs_distance = row.get(abs_distance_col)

        # 如果有部件/缺陷类型列，优先使用它来判断
        if weld_type_col is not None:
            weld_type = row.get(weld_type_col)
            if (pd.notna(weld_type) and str(weld_type).strip() == '环焊缝' and
                    pd.notna(abs_distance) and str(abs_distance).strip() != ''):
                try:
                    weld_number = row.get(weld_number_col)
                    pipe_num = int(float(str(weld_number).strip())) if pd.notna(weld_number) else None
                    abs_dist = float(str(abs_distance).strip())
                    if pipe_num is None:
                        pipe_num = now_pipe_num
                        now_pipe_num = now_pipe_num + 10
                    weld_data.append((pipe_num, abs_dist))
                except (ValueError, TypeError):
                    continue
        # 如果没有部件/缺陷类型列，使用上游环焊缝编号判断
        elif weld_number_col is not None:
            weld_number = row.get(weld_number_col)
            if (pd.notna(weld_number) and pd.notna(abs_distance) and
                    str(weld_number).strip() != '' and str(abs_distance).strip() != ''):
                try:
                    weld_num = int(float(str(weld_number).strip()))
                    abs_dist = float(str(abs_distance).strip())
                    weld_data.append((weld_num, abs_dist))
                except (ValueError, TypeError):
                    continue

    # 按绝对距离排序
    weld_data.sort(key=lambda x: x[1])

    # 提取绝对距离和焊缝编号
    absolute_distances = [item[1] for item in weld_data]
    weld_numbers = [item[0] for item in weld_data]

    # 计算相对距离
    relative_distances = [0]
    for i in range(len(absolute_distances) - 1):
        relative_distances.append(round(absolute_distances[i + 1] - absolute_distances[i], 4))

    return absolute_distances, relative_distances, weld_numbers


def read_defect_data(df, file_type=1):
    """
    统一的缺陷数据读取函数

    Args:
        df: 数据框
        file_type: 文件类型，1或2，用于区分不同的文件格式

    Returns:
        list: 缺陷数据列表
    """
    # 查找相关列
    weld_number_col = None
    abs_distance_col = None
    orientation_col = None
    depth_col = None
    length_col = None
    width_col = None
    comment_col = None
    defect_type_col = None

    for col in df.columns:
        col_str = str(col).lower()
        if '上游环焊缝编号' in col_str:
            weld_number_col = col
        elif '绝对距离' in col_str:
            abs_distance_col = col
        elif '时钟方位' in col_str:
            orientation_col = col
        elif '深度' in col_str:
            depth_col = col
        elif '长度' in col_str and 'mm' in col_str:
            length_col = col
        elif '宽度' in col_str and 'mm' in col_str:
            width_col = col
        elif '部件/缺陷类型' in col_str:
            comment_col = col
        elif '部件/缺陷识别' in col_str:
            defect_type_col = col

    # 如果没有找到特定的长度/宽度列，尝试查找通用的
    if length_col is None:
        for col in df.columns:
            if '长度' in str(col).lower():
                length_col = col
                break

    if width_col is None:
        for col in df.columns:
            if '宽度' in str(col).lower():
                width_col = col
                break

    defects = []

    for idx, row in df.iterrows():
        # 检查是否有缺陷数据（深度、长度、宽度至少有一个不为空）
        has_defect_data = False
        # for col in [depth_col, length_col, width_col]:
        for col in [depth_col]:
            if col and pd.notna(row.get(col)) and str(row.get(col)).strip() != '':
                has_defect_data = True
                break

        if not has_defect_data:
            continue

        # 获取最近的环焊缝编号和绝对距离
        current_weld = None
        current_abs_distance = None

        # 向上查找最近的环焊缝 - 修正逻辑
        # 环焊缝的特征：上游环焊缝编号不为空，且深度、长度、宽度都为空
        for i in range(idx, -1, -1):
            search_row = df.iloc[i]
            weld_num = search_row.get(weld_number_col)
            abs_dist = search_row.get(abs_distance_col)

            # 检查深度、长度、宽度是否都为空
            depth_empty = depth_col is None or pd.isna(search_row.get(depth_col)) or str(
                search_row.get(depth_col)).strip() == ''
            length_empty = length_col is None or pd.isna(search_row.get(length_col)) or str(
                search_row.get(length_col)).strip() == ''
            width_empty = width_col is None or pd.isna(search_row.get(width_col)) or str(
                search_row.get(width_col)).strip() == ''

            # 环焊缝条件：上游环焊缝编号不为空，绝对距离不为空，且深度、长度、宽度都为空
            if (pd.notna(weld_num) and pd.notna(abs_dist) and
                    str(weld_num).strip() != '' and str(abs_dist).strip() != '' and
                    depth_empty and length_empty and width_empty):
                try:
                    current_weld = int(float(str(weld_num).strip()))
                    current_abs_distance = float(str(abs_dist).strip())
                    break
                except (ValueError, TypeError):
                    continue

        if current_weld is None:
            # 如果向上找不到环焊缝，尝试向下查找
            for i in range(idx, min(idx + 10, len(df))):
                search_row = df.iloc[i]
                weld_num = search_row.get(weld_number_col)
                abs_dist = search_row.get(abs_distance_col)

                # 检查深度、长度、宽度是否都为空
                depth_empty = depth_col is None or pd.isna(search_row.get(depth_col)) or str(
                    search_row.get(depth_col)).strip() == ''
                length_empty = length_col is None or pd.isna(search_row.get(length_col)) or str(
                    search_row.get(length_col)).strip() == ''
                width_empty = width_col is None or pd.isna(search_row.get(width_col)) or str(
                    search_row.get(width_col)).strip() == ''

                if (pd.notna(weld_num) and pd.notna(abs_dist) and
                        str(weld_num).strip() != '' and str(abs_dist).strip() != '' and
                        depth_empty and length_empty and width_empty):
                    try:
                        current_weld = int(float(str(weld_num).strip()))
                        current_abs_distance = float(str(abs_dist).strip())
                        break
                    except (ValueError, TypeError):
                        continue

        if current_weld is None:
            continue

        # 计算到上游环焊缝的距离
        defect_abs_distance = row.get(abs_distance_col)
        if pd.notna(defect_abs_distance) and str(defect_abs_distance).strip() != '':
            try:
                defect_abs_dist = float(str(defect_abs_distance).strip())
                distance_to_weld = defect_abs_dist - current_abs_distance
            except (ValueError, TypeError):
                distance_to_weld = 0
        else:
            distance_to_weld = 0

        # 处理时钟方位（转换为度数）
        clock_position = 0
        orientation = row.get(orientation_col)
        if pd.notna(orientation) and str(orientation).strip() != '':
            clock_position = convert_clock_to_degrees(str(orientation).strip())

        # 获取缺陷参数
        depth = get_float_value(row.get(depth_col))
        length = get_float_value(row.get(length_col))
        width = get_float_value(row.get(width_col))

        # 获取注释和缺陷类型
        comment = ""
        defect_type = ""

        if comment_col and pd.notna(row.get(comment_col)):
            comment = str(row.get(comment_col))
            defect_type = classify_defect_type(comment)

        if defect_type_col and pd.notna(row.get(defect_type_col)):
            defect_type = str(row.get(defect_type_col))
        elif not defect_type and comment:
            defect_type = classify_defect_type(comment)

        defect = {
            'weld_number': str(current_weld),
            'distance_to_weld': round(distance_to_weld, 3),
            'clock_position': clock_position,
            'depth': depth,
            'length': length,
            'width': width,
            'defect_type': defect_type,
            'comment': comment,
            'original_index': idx,
            'absolute_distance': defect_abs_dist if 'defect_abs_dist' in locals() else current_abs_distance
        }
        defects.append(defect)

    return defects


def convert_clock_to_degrees(clock_time):
    """
    将时钟方位转换为度数

    Args:
        clock_time: 时钟方位字符串，如 "12:00", "06:30:00"

    Returns:
        float: 度数 (0-360)
    """
    try:
        # 清理字符串
        clock_time = clock_time.strip()

        # 匹配时间格式
        time_parts = re.findall(r'\d+', clock_time)

        if len(time_parts) >= 2:
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = int(time_parts[2]) if len(time_parts) > 2 else 0

            # 转换为度数 (12小时制，12点对应0度，顺时针增加)
            total_minutes = minutes + seconds / 60
            degrees = (hours % 12) * 30 + total_minutes * 0.5

            return degrees % 360
        else:
            return 0
    except (ValueError, TypeError):
        return 0


def get_float_value(value):
    """
    安全地获取浮点数值

    Args:
        value: 输入值

    Returns:
        float: 转换后的浮点数，转换失败返回0
    """
    if pd.isna(value) or value == '':
        return 0
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return 0


def classify_defect_type(comment):
    """
    根据注释分类缺陷类型

    Args:
        comment: 注释文本

    Returns:
        str: 缺陷类型
    """
    comment_lower = comment.lower()

    if 'mfg' in comment_lower or '制造' in comment_lower:
        return '管体制造缺陷'
    elif 'corrosion' in comment_lower or '腐蚀' in comment_lower:
        return '腐蚀'
    elif 'mechanical' in comment_lower or '机械' in comment_lower:
        return '机械损伤'
    else:
        return '未知缺陷'


def calculate_defect_similarity(defect1, defect2, thresholds):
    """
    计算两个缺陷的相似度

    Args:
        defect1: 缺陷1数据
        defect2: 缺陷2数据
        thresholds: 阈值配置

    Returns:
        tuple: (置信度, 说明)
    """
    # 计算距离差异
    distance_diff = abs(defect1['distance_to_weld'] - defect2['distance_to_weld'])
    distance_score = max(0, 1 - distance_diff / thresholds['distance'])

    # 计算时钟方位差异
    clock_diff = min(
        abs(defect1['clock_position'] - defect2['clock_position']),
        360 - abs(defect1['clock_position'] - defect2['clock_position'])
    )
    clock_score = max(0, 1 - clock_diff / thresholds['clock_position'])

    # 计算长度差异
    length_diff = abs(defect1['length'] - defect2['length'])
    length_score = max(0, 1 - length_diff / thresholds['length']) if defect1['length'] > 0 and defect2[
        'length'] > 0 else 0.5

    # 计算深度差异
    depth_diff = abs(defect1['depth'] - defect2['depth'])
    depth_score = max(0, 1 - depth_diff / thresholds['depth']) if defect1['depth'] > 0 and defect2['depth'] > 0 else 0.5

    # 计算缺陷类型相似度
    type_score = 0.5
    type1 = defect1.get('defect_type', '').lower()
    type2 = defect2.get('defect_type', '').lower()

    if type1 and type2:
        if '腐蚀' in type1 and '腐蚀' in type2:
            type_score = 1.0
        elif '制造' in type1 and '制造' in type2:
            type_score = 1.0
        elif type1 == type2:
            type_score = 1.0
        elif any(word in type1 for word in ['mfg', 'manufacture']) and any(word in type2 for word in ['制造']):
            type_score = 0.8

    # 计算综合置信度（加权平均）
    weights = {
        'distance': 0.75,
        'clock': 0.25,
        'length': 0,
        'depth': 0,
        'type': 0
    }

    total_confidence = (
            distance_score * weights['distance'] +
            clock_score * weights['clock'] +
            length_score * weights['length'] +
            depth_score * weights['depth'] +
            type_score * weights['type']
    )

    # 生成匹配说明
    explanation_parts = []
    if distance_score > 0.8:
        explanation_parts.append("距离匹配良好")
    elif distance_score > 0.5:
        explanation_parts.append("距离基本匹配")
    else:
        explanation_parts.append("距离差异较大")

    if clock_score > 0.8:
        explanation_parts.append("方位匹配良好")
    elif clock_score > 0.5:
        explanation_parts.append("方位基本匹配")
    else:
        explanation_parts.append("方位差异较大")

    if type_score > 0.7:
        explanation_parts.append("类型匹配")

    explanation = "; ".join(explanation_parts)

    return total_confidence, explanation


def calculate_weld_statistics(rel_dist1: List[float], rel_dist2: List[float]) -> Dict[str, float]:
    """
    基于两个文件的相对距离数据计算统计特征
    用于自适应阈值设置
    """
    # 合并两个文件的相对距离，过滤掉0值（起始点）
    all_redis = [d for d in rel_dist1 + rel_dist2 if d > 0]

    if not all_redis:
        return {
            'mean': 10.0,
            'std': 2.0,
            'cv': 0.2,
            'q25': 8.0,
            'q50': 10.0,
            'q75': 12.0,
            'iqr': 4.0
        }

    redis_array = np.array(all_redis)

    # 计算基本统计量
    mean_val = np.mean(redis_array)
    std_val = np.std(redis_array)
    cv = std_val / mean_val if mean_val > 0 else 0  # 变异系数

    # 计算分位数
    q25 = np.percentile(redis_array, 25)
    q50 = np.percentile(redis_array, 50)
    q75 = np.percentile(redis_array, 75)
    iqr = q75 - q25  # 四分位距

    # 识别异常值边界
    lower_bound = q25 - 1.5 * iqr
    upper_bound = q75 + 1.5 * iqr

    # 过滤异常值后的统计
    filtered_redis = [d for d in all_redis if lower_bound <= d <= upper_bound]
    if filtered_redis:
        filtered_array = np.array(filtered_redis)
        filtered_mean = np.mean(filtered_array)
        filtered_std = np.std(filtered_array)
        filtered_cv = filtered_std / filtered_mean if filtered_mean > 0 else 0
    else:
        filtered_mean = mean_val
        filtered_std = std_val
        filtered_cv = cv

    print(f"环焊缝相对距离统计:")
    print(f"  均值: {mean_val:.2f}, 标准差: {std_val:.2f}, 变异系数: {cv:.3f}")
    print(f"  分位数: Q25={q25:.2f}, Q50={q50:.2f}, Q75={q75:.2f}, IQR={iqr:.2f}")
    print(f"  过滤异常值后 - 均值: {filtered_mean:.2f}, 标准差: {filtered_std:.2f}, 变异系数: {filtered_cv:.3f}")

    return {
        'mean': mean_val,
        'std': std_val,
        'cv': cv,
        'q25': q25,
        'q50': q50,
        'q75': q75,
        'iqr': iqr,
        'filtered_mean': filtered_mean,
        'filtered_std': filtered_std,
        'filtered_cv': filtered_cv
    }


def comprehensive_weld_alignment(weld_numbers1: List[str], absolute_distances1: List[float], redis1: List[float],
                                 weld_numbers2: List[str], absolute_distances2: List[float], redis2: List[float],
                                 base_distance: float = 50.0, similarity_threshold: float = 0.1) -> WeldAlignment:
    """
    改进的环焊缝对齐算法 - 保留初始匹配，后续使用基于固定距离的累加匹配方法

    Args:
        weld_numbers1: 文件1环焊缝编号列表
        absolute_distances1: 文件1绝对距离列表
        redis1: 文件1相对距离列表
        weld_numbers2: 文件2环焊缝编号列表
        absolute_distances2: 文件2绝对距离列表
        redis2: 文件2相对距离列表
        base_distance: 基础距离阈值（米），默认为50米
        similarity_threshold: 相似度阈值，默认为0.1（10%）

    Returns:
        WeldAlignment: 环焊缝对齐结果
    """
    result = WeldAlignment()
    result.base_distance = base_distance  # 记录使用的基础距离

    statistics = calculate_weld_statistics(redis1, redis2)
    cv = statistics['filtered_cv']
    mean_redis = statistics['filtered_mean']
    std_redis = statistics['filtered_std']
    iqr = statistics['iqr']

    # 段落基准距离相似度
    if cv < 0.1:  # 数据很集中，高质量
        similarity_threshold = 0.1
    elif cv < 0.25:  # 数据较集中
        similarity_threshold = 0.15
    elif cv < 0.5:  # 数据一般离散
        similarity_threshold = 0.2
    else:  # 数据很离散
        similarity_threshold = 0.25

    # 环焊缝相似度
    if mean_redis < 5.0:  # 小距离
        abs_threshold = 0.2
        rel_threshold = 0.07
    elif mean_redis < 15.0:  # 中等距离
        abs_threshold = 0.3
        rel_threshold = 0.06
    else:  # 大距离
        abs_threshold = 0.5
        rel_threshold = 0.05

    len1, len2 = len(redis1), len(redis2)
    if len1 < 5 or len2 < 5:
        min_match_count = min(2, min(len1, len2))
        # threshold = 1.0
    else:
        min_match_count = 4
        # threshold = 0.2

    # 保留原有的起始点匹配逻辑
    found_start = False
    max_search_distance = min(len(redis1), len(redis2)) // 2  # 最大搜索距离
    begin1, begin2, num1, num2 = 0, 0, 0, 0
    weld1_idx, weld2_idx = 0, 0
    match_count = 0

    # 搜索匹配的起始点
    for start1 in range(min(50, len(redis1))):  # 限制搜索范围，避免性能问题
        for start2 in range(min(50, len(redis2))):
            count = 0
            i, j = start1, start2
            # 检查从当前起始点开始的连续匹配
            while i < len(redis1) and j < len(redis2) and count < min_match_count:
                if abs(redis1[i] - redis2[j]) < abs_threshold:
                    count += 1
                    i += 1
                    j += 1
                else:
                    break

            if count >= min_match_count:  # 找到匹配的起始点
                begin1 = start1
                begin2 = start2
                num1 = start1 + count
                num2 = start2 + count
                match_count = count
                found_start = True
                break
        if found_start:
            break

    if not found_start:
        # 如果没有找到匹配的起始点，使用默认的起始点
        print("未找到匹配的起始点，使用默认起始点")
        begin1 = 0
        begin2 = 0
        num1 = 0
        num2 = 0

    # 写入起始匹配点之前的数据
    if found_start:
        print(f"找到匹配起始点: 文件1位置{begin1}, 文件2位置{begin2}, 匹配数量{match_count}")

        # 写入第一个文件起始点之前的数据
        if begin1 > 0:
            for i in range(begin1 - 1):
                result.add_alignment(
                    weld1=weld_numbers1[i],
                    dist1=absolute_distances1[i],
                    redis1=redis1[i] if i > 0 else 0
                )
                weld1_idx += 1

        # 写入第二个文件起始点之前的数据
        if begin2 > 0:
            for i in range(begin2 - 1):
                result.add_alignment(
                    weld2=weld_numbers2[i],
                    dist2=absolute_distances2[i],
                    redis2=redis2[i] if i > 0 else 0
                )
                weld2_idx += 1
        result.add_alignment(weld1=weld_numbers1[begin1 - 1],
                             dist1=absolute_distances1[begin1 - 1],
                             redis1=redis1[begin1 - 1],
                             weld2=weld_numbers2[begin2 - 1],
                             dist2=absolute_distances2[begin2 - 1],
                             redis2=redis2[begin2 - 1]
                             )
        weld1_idx += 1
        weld2_idx += 1

        # 写入匹配的起始段
        for i in range(match_count):
            idx1 = begin1 + i
            idx2 = begin2 + i
            confidence = max(0, 1 - (abs(redis1[idx1] - redis2[idx2]) / abs_threshold))
            result.add_alignment(
                weld1=weld_numbers1[idx1],
                dist1=absolute_distances1[idx1],
                redis1=redis1[idx1],
                weld2=weld_numbers2[idx2],
                dist2=absolute_distances2[idx2],
                redis2=redis2[idx2],
                confidence=confidence
            )
            weld1_idx += 1
            weld2_idx += 1

    # 更新索引，准备进行后续的基于固定距离的累加匹配
    i, j = weld1_idx, weld2_idx

    print(f"初始匹配完成，开始基于固定距离的累加匹配，基础距离: {base_distance}米")

    # 基于固定距离的累加匹配 - 改进逻辑
    while i < len1 and j < len2:
        # 阶段1: 累加相对距离直到超过基准距离
        accum1, segment1, k = accumulate_until_threshold(redis1, i, base_distance)
        accum2, segment2, l = accumulate_until_threshold(redis2, j, base_distance)

        # 阶段2: 调整累加距离直到相似
        while (k < len1 or l < len2) and not is_similar(accum1, accum2, similarity_threshold):
            if accum1 < accum2:
                # 文件1累加距离较小，继续增加环焊缝
                if k < len1:
                    accum1 += redis1[k]
                    segment1.append(k)
                    k += 1
                else:
                    break  # 文件1已到末尾
            else:
                # 文件2累加距离较小，继续增加环焊缝
                if l < len2:
                    accum2 += redis2[l]
                    segment2.append(l)
                    l += 1
                else:
                    break  # 文件2已到末尾

        # 阶段3: 对段落内的环焊缝进行一一匹配
        if is_similar(accum1, accum2, similarity_threshold) and len(segment1) > 0 and len(segment2) > 0:
            # 对齐这两个段落中的环焊缝
            align_segments(result, weld_numbers1, absolute_distances1, redis1,
                           weld_numbers2, absolute_distances2, redis2,
                           segment1, segment2, abs_threshold, rel_threshold)

            # 更新索引
            i = k
            j = l
        else:
            # 如果段落匹配失败，尝试单个环焊缝匹配
            if align_single_weld(result, weld_numbers1, absolute_distances1, redis1[i],
                                 weld_numbers2, absolute_distances2, redis2[j], abs_threshold):
                # 单个环焊缝匹配成功
                i += 1
                j += 1
            else:
                # 单个环焊缝也不匹配，分别处理
                if redis1[i] <= redis2[j]:
                    result.add_alignment(
                        weld1=weld_numbers1[i],
                        dist1=absolute_distances1[i],
                        redis1=redis1[i]
                    )
                    i += 1
                else:
                    result.add_alignment(
                        weld2=weld_numbers2[j],
                        dist2=absolute_distances2[j],
                        redis2=redis2[j]
                    )
                    j += 1

    # 处理剩余的环焊缝
    while i < len1:
        result.add_alignment(
            weld1=weld_numbers1[i],
            dist1=absolute_distances1[i],
            redis1=redis1[i]
        )
        i += 1

    while j < len2:
        result.add_alignment(
            weld2=weld_numbers2[j],
            dist2=absolute_distances2[j],
            redis2=redis2[j]
        )
        j += 1

    # 计算对齐的环焊缝对数
    result.count_aligned_welds()

    return result


def accumulate_until_threshold(redis_list, start_idx, threshold):
    """
    从指定索引开始累加相对距离，直到超过阈值

    Args:
        redis_list: 相对距离列表
        start_idx: 起始索引
        threshold: 阈值

    Returns:
        tuple: (累加和, 包含的索引列表, 下一个索引)
    """
    accum = 0
    segments = []
    idx = start_idx

    while idx < len(redis_list) and accum < threshold:
        accum += redis_list[idx]
        segments.append(idx)
        idx += 1

    return accum, segments, idx


def is_similar(value1, value2, threshold):
    """
    判断两个值是否相似

    Args:
        value1: 值1
        value2: 值2
        threshold: 相似度阈值

    Returns:
        bool: 是否相似
    """
    if value1 == 0 and value2 == 0:
        return True
    if value1 == 0 or value2 == 0:
        return False

    # align1 = abs(value1 - value2) / value1
    # align2 = abs(value1 - value2) / value2
    # return align1 < threshold or align2 < threshold
    similarity = 1 - abs(value1 - value2) / max(value1, value2)
    return similarity >= (1 - threshold)


def align_segments(result, weld_numbers1, absolute_distances1, redis1,
                   weld_numbers2, absolute_distances2, redis2,
                   segment1, segment2, abs_threshold, rel_threshold):
    """
    对齐两个段落中的环焊缝
    基于相对距离小的文件内环焊缝向下增加，通过累加相对距离来实现匹配

    Args:
        result: 对齐结果对象
        weld_numbers1: 文件1环焊缝编号列表
        absolute_distances1: 文件1绝对距离列表
        redis1: 文件1相对距离列表
        weld_numbers2: 文件2环焊缝编号列表
        absolute_distances2: 文件2绝对距离列表
        redis2: 文件2相对距离列表
        segment1: 文件1段落索引列表
        segment2: 文件2段落索引列表
        abs_threshold: 绝对距离相似度阈值
        rel_threshold: 相对距离相似度阈值
    """
    i, j = 0, 0

    # 当前累加的相对距离
    current_redis1 = redis1[segment1[i]]
    current_redis2 = redis2[segment2[j]]

    # 当前处理的环焊缝索引
    current_idx1 = -1
    current_idx2 = -1
    while i < len(segment1) and j < len(segment2):
        if abs(current_redis1 - current_redis2)/current_redis1 < rel_threshold \
                or abs(current_redis1 - current_redis2)/current_redis2 < rel_threshold \
                or abs(current_redis1 - current_redis2) < abs_threshold:
            confidence = max(0, 1 - (
                        2 * abs(current_redis1 - current_redis2) / (current_redis1 + current_redis2) / abs_threshold))
            result.add_alignment(
                weld1=weld_numbers1[segment1[i]],
                dist1=absolute_distances1[segment1[i]],
                redis1=redis1[segment1[i]],
                weld2=weld_numbers2[segment2[j]],
                dist2=absolute_distances2[segment2[j]],
                redis2=redis2[segment2[j]],
                confidence=confidence
            )
            i += 1
            j += 1
            if i < len(segment1) and j < len(segment2):
                current_redis1 = redis1[segment1[i]]
                current_redis2 = redis2[segment2[j]]
        elif current_redis1 < current_redis2:
            result.add_alignment(
                weld1=weld_numbers1[segment1[i]],
                dist1=absolute_distances1[segment1[i]],
                redis1=redis1[segment1[i]]
            )
            i += 1
            if i < len(segment1):
                current_redis1 = current_redis1 + redis1[segment1[i]]
        else:
            result.add_alignment(
                weld2=weld_numbers2[segment2[j]],
                dist2=absolute_distances2[segment2[j]],
                redis2=redis2[segment2[j]]
            )
            j += 1
            if j < len(segment2):
                current_redis2 = current_redis2 + redis2[segment2[j]]
    # while i < len(segment1) and j < len(segment2):
    #     # 如果是新的环焊缝，初始化当前累加距离
    #     if current_idx1 != i:
    #         current_redis1 = redis1[segment1[i]]
    #         current_idx1 = i
    #
    #     if current_idx2 != j:
    #         current_redis2 = redis2[segment2[j]]
    #         current_idx2 = j
    #
    #     # 检查当前累加距离是否相似
    #     if is_similar(current_redis1, current_redis2, 0.06):  # 使用6%的阈值
    #         # 匹配成功
    #         confidence = max(0,
    #                    1 - (2 * abs(current_redis1 - current_redis2) / (current_redis1 + current_redis2) / threshold))
    #         result.add_alignment(
    #             weld1=weld_numbers1[segment1[i]],
    #             dist1=absolute_distances1[segment1[i]],
    #             redis1=redis1[segment1[i]],
    #             weld2=weld_numbers2[segment2[j]],
    #             dist2=absolute_distances2[segment2[j]],
    #             redis2=redis2[segment2[j]],
    #             confidence=confidence
    #         )
    #         i += 1
    #         j += 1
    #         # 重置当前累加距离
    #         current_redis1 = 0
    #         current_redis2 = 0
    #         current_idx1 = -1
    #         current_idx2 = -1
    #
    #     elif current_redis1 < current_redis2:
    #         # 文件1的当前累加距离较小，向下增加环焊缝
    #         if i + 1 < len(segment1):
    #             i += 1
    #             current_redis1 += redis1[segment1[i]]
    #             current_idx1 = i
    #         else:
    #             # 文件1已到末尾，无法继续累加
    #             result.add_alignment(
    #                 weld1=weld_numbers1[segment1[i]],
    #                 dist1=absolute_distances1[segment1[i]],
    #                 redis1=redis1[segment1[i]]
    #             )
    #             i += 1
    #             # 重置当前累加距离
    #             current_redis1 = 0
    #             current_idx1 = -1
    #
    #     else:
    #         # 文件2的当前累加距离较小，向下增加环焊缝
    #         if j + 1 < len(segment2):
    #             j += 1
    #             current_redis2 += redis2[segment2[j]]
    #             current_idx2 = j
    #         else:
    #             # 文件2已到末尾，无法继续累加
    #             result.add_alignment(
    #                 weld2=weld_numbers2[segment2[j]],
    #                 dist2=absolute_distances2[segment2[j]],
    #                 redis2=redis2[segment2[j]]
    #             )
    #             j += 1
    #             # 重置当前累加距离
    #             current_redis2 = 0
    #             current_idx2 = -1

    # 处理段落中剩余的环焊缝
    while i < len(segment1):
        result.add_alignment(
            weld1=weld_numbers1[segment1[i]],
            dist1=absolute_distances1[segment1[i]],
            redis1=redis1[segment1[i]]
        )
        i += 1

    while j < len(segment2):
        result.add_alignment(
            weld2=weld_numbers2[segment2[j]],
            dist2=absolute_distances2[segment2[j]],
            redis2=redis2[segment2[j]]
        )
        j += 1


def align_single_weld(result, weld_numbers1, absolute_distances1, redis1,
                      weld_numbers2, absolute_distances2, redis2, threshold):
    """
    尝试对齐单个环焊缝

    Args:
        result: 对齐结果对象
        weld_numbers1: 文件1环焊缝编号列表
        absolute_distances1: 文件1绝对距离列表
        redis1: 文件1相对距离值
        weld_numbers2: 文件2环焊缝编号列表
        absolute_distances2: 文件2绝对距离列表
        redis2: 文件2相对距离值
        threshold: 相似度阈值

    Returns:
        bool: 是否匹配成功
    """
    if is_similar(redis1, redis2, 0.2):  # 使用更宽松的阈值
        confidence = max(0, 1 - (abs(redis1 - redis2) / threshold))
        result.add_alignment(
            weld1=weld_numbers1,
            dist1=absolute_distances1,
            redis1=redis1,
            weld2=weld_numbers2,
            dist2=absolute_distances2,
            redis2=redis2,
            confidence=confidence
        )
        return True
    return False


def align_defects_with_comprehensive_mapping(defects1: List[Dict], defects2: List[Dict],
                                             weld_alignment: WeldAlignment, thresholds: Dict = None) -> pd.DataFrame:
    """
    使用全面的环焊缝对齐结果进行缺陷对齐，包括未对齐环焊缝的缺陷
    确保每个未匹配缺陷仅出现一次
    """
    if thresholds is None:
        thresholds = {
            'distance': 1.0,  # 距离阈值（米）
            'clock_position': 45,  # 时钟方位阈值（度）
            'length': 10,  # 长度阈值（mm）
            'depth': 2,  # 深度阈值（%或mm）
            'min_confidence': 0.6  # 最小置信度
        }

    # 初始化结果DataFrame
    result_columns = [
        '文件1缺陷ID', '文件1环焊缝', '文件1到焊缝距离', '文件1时钟方位',
        '文件1缺陷类型', '文件1深度', '文件1长度', '文件1宽度', '文件1注释', '文件1绝对距离',
        '文件2缺陷ID', '文件2环焊缝', '文件2到焊缝距离', '文件2时钟方位',
        '文件2缺陷类型', '文件2深度', '文件2长度', '文件2宽度', '文件2注释', '文件2绝对距离',
        '匹配置信度', '匹配说明', '匹配类型'
    ]
    result_df = pd.DataFrame(columns=result_columns)

    matched_defects2 = set()
    processed_defects1 = set()  # 跟踪已处理的文件1缺陷

    # 第一阶段：处理已对齐环焊缝的缺陷
    print("第一阶段：处理已对齐环焊缝的缺陷...")
    for defect1 in defects1:
        defect1_id = id(defect1)
        if defect1_id in processed_defects1:
            continue  # 跳过已处理的缺陷

        best_match = None
        best_confidence = 0
        best_explanation = ""
        match_type = "未匹配"

        weld1 = defect1['weld_number']
        mapped_weld2 = weld_alignment.get_file2_weld(weld1)

        if mapped_weld2:
            # 在文件2中查找相同焊缝的缺陷
            candidate_defects = []
            for defect2 in defects2:
                if (defect2['weld_number'] == mapped_weld2 and
                        id(defect2) not in matched_defects2):
                    candidate_defects.append(defect2)

            for defect2 in candidate_defects:
                confidence, explanation = calculate_defect_similarity(defect1, defect2, thresholds)

                if confidence > best_confidence:
                    best_match = defect2
                    best_confidence = confidence
                    best_explanation = explanation

            if best_match and best_confidence >= thresholds['min_confidence']:
                matched_defects2.add(id(best_match))
                match_type = "环焊缝对齐匹配"
                result_df = _append_defect_alignment_result(
                    result_df, defect1, best_match, best_confidence, best_explanation, match_type
                )
                processed_defects1.add(defect1_id)  # 标记为已处理
            else:
                match_type = "环焊缝对齐但缺陷未匹配"
                result_df = _append_defect_alignment_result(
                    result_df, defect1, None, best_confidence,
                    f"未找到匹配缺陷" if not best_match else f"置信度过低: {best_confidence:.2f}",
                    match_type
                )
                processed_defects1.add(defect1_id)  # 标记为已处理

    # 第二阶段：处理未对齐环焊缝的缺陷（仅处理第一阶段未处理的）
    print("第二阶段：处理未对齐环焊缝的缺陷...")
    for defect1 in defects1:
        defect1_id = id(defect1)
        if defect1_id in processed_defects1:
            continue  # 跳过已处理的缺陷

        best_match = None
        best_confidence = 0
        best_explanation = ""
        match_type = "未匹配"

        defect1_abs_distance = defect1.get('absolute_distance', 0)

        # 查找最近的已对齐环焊缝
        nearest_aligned = weld_alignment.get_nearest_aligned_weld1(defect1_abs_distance)

        if nearest_aligned:
            # 计算相对于最近对齐环焊缝的相对距离
            relative_distance = defect1_abs_distance - nearest_aligned['distance']
            expected_distance2 = nearest_aligned['aligned_distance2'] + relative_distance

            # 在文件2中查找距离最近的缺陷
            candidate_defects = []
            for defect2 in defects2:
                if id(defect2) not in matched_defects2:
                    defect2_abs_distance = defect2.get('absolute_distance', 0)
                    distance_diff = abs(defect2_abs_distance - expected_distance2)
                    if distance_diff < thresholds['distance'] * 2:  # 放宽距离阈值
                        candidate_defects.append((defect2, distance_diff))

            # 按距离排序，选择最近的几个候选
            candidate_defects.sort(key=lambda x: x[1])
            candidate_defects = candidate_defects[:5]  # 只考虑前5个最近的候选

            for defect2, dist_diff in candidate_defects:
                confidence, explanation = calculate_defect_similarity(defect1, defect2, thresholds)

                # 根据距离差异调整置信度
                distance_penalty = dist_diff / (thresholds['distance'] * 2)
                adjusted_confidence = max(0, confidence - distance_penalty * 0.3)

                if adjusted_confidence > best_confidence:
                    best_match = defect2
                    best_confidence = adjusted_confidence
                    best_explanation = f"{explanation}; 基于相对距离匹配"

            if best_match and best_confidence >= thresholds['min_confidence'] * 0.8:  # 降低阈值
                matched_defects2.add(id(best_match))
                match_type = "相对距离匹配"
                result_df = _append_defect_alignment_result(
                    result_df, defect1, best_match, best_confidence, best_explanation, match_type
                )
            else:
                match_type = "未匹配"
                result_df = _append_defect_alignment_result(
                    result_df, defect1, None, best_confidence,
                    f"基于相对距离未找到匹配缺陷", match_type
                )
        else:
            # 没有找到已对齐的环焊缝作为参考
            match_type = "未匹配"
            result_df = _append_defect_alignment_result(
                result_df, defect1, None, 0,
                f"无法确定参考环焊缝", match_type
            )

        processed_defects1.add(defect1_id)  # 标记为已处理

    # 第三阶段：处理文件2中剩余的未匹配缺陷
    print("第三阶段：处理文件2中剩余的未匹配缺陷...")
    for defect2 in defects2:
        if id(defect2) not in matched_defects2:
            weld2 = defect2['weld_number']
            mapped_weld1 = weld_alignment.get_file1_weld(weld2)

            if mapped_weld1:
                explanation = f"环焊缝已对齐，但缺陷无对应"
            else:
                # 尝试基于相对距离匹配
                defect2_abs_distance = defect2.get('absolute_distance', 0)
                nearest_aligned = weld_alignment.get_nearest_aligned_weld2(defect2_abs_distance)

                if nearest_aligned:
                    explanation = f"基于相对距离未找到匹配"
                else:
                    explanation = f"环焊缝{weld2}在文件1中无对应"

            result_df = _append_defect_alignment_result(
                result_df, None, defect2, 0, explanation, "文件2未匹配缺陷"
            )

    return result_df


def _append_defect_alignment_result(df, defect1, defect2, confidence, explanation, match_type):
    """
    向缺陷对齐结果DataFrame添加一行数据
    """
    new_row = {
        '文件1缺陷ID': defect1['original_index'] + 2 if defect1 else '',
        '文件1环焊缝': defect1['weld_number'] if defect1 else '',
        '文件1到焊缝距离': f"{defect1['distance_to_weld']:.3f}" if defect1 else '',
        '文件1时钟方位': f"{defect1['clock_position']:.1f}" if defect1 else '',
        '文件1缺陷类型': defect1.get('defect_type', '') if defect1 else '',
        '文件1深度': f"{defect1['depth']:.2f}" if defect1 else '',
        '文件1长度': f"{defect1['length']:.1f}" if defect1 else '',
        '文件1宽度': f"{defect1['width']:.1f}" if defect1 else '',
        '文件1注释': defect1.get('comment', '') if defect1 else '',
        '文件1绝对距离': f"{defect1.get('absolute_distance', 0):.3f}" if defect1 else '',
        '文件2缺陷ID': defect2['original_index'] + 2 if defect2 else '',
        '文件2环焊缝': defect2['weld_number'] if defect2 else '',
        '文件2到焊缝距离': f"{defect2['distance_to_weld']:.3f}" if defect2 else '',
        '文件2时钟方位': f"{defect2['clock_position']:.1f}" if defect2 else '',
        '文件2缺陷类型': defect2.get('defect_type', '') if defect2 else '',
        '文件2深度': f"{defect2['depth']:.2f}" if defect2 else '',
        '文件2长度': f"{defect2['length']:.1f}" if defect2 else '',
        '文件2宽度': f"{defect2['width']:.1f}" if defect2 else '',
        '文件2注释': defect2.get('comment', '') if defect2 else '',
        '文件2绝对距离': f"{defect2.get('absolute_distance', 0):.3f}" if defect2 else '',
        '匹配置信度': f"{confidence:.3f}" if confidence > 0 else '',
        '匹配说明': explanation,
        '匹配类型': match_type
    }
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)


def sort_weld_alignment_results(weld_alignment: WeldAlignment) -> List[Dict]:
    """
    对环焊缝对齐结果按里程排序

    Args:
        weld_alignment: 环焊缝对齐结果

    Returns:
        List[Dict]: 排序后的环焊缝对齐结果
    """
    # 合并所有焊缝数据
    all_welds = []

    # 添加对齐的焊缝
    for alignment in weld_alignment.alignments:
        if alignment['file1_distance'] != 0 and alignment['file2_distance'] != 0:
            all_welds.append({
                '类型': '对齐',
                '文件1环焊缝': alignment['file1_weld'],
                '文件1绝对距离': alignment['file1_distance'],
                '文件1相对距离': alignment['file1_redis'],
                '文件2环焊缝': alignment['file2_weld'],
                '文件2绝对距离': alignment['file2_distance'],
                '文件2相对距离': alignment['file2_redis'],
                '对齐置信度': alignment['confidence']
            })
        elif alignment['file1_distance'] == 0:
            all_welds.append({
                '类型': '文件2未对齐',
                '文件1环焊缝': alignment['file1_weld'],
                '文件1绝对距离': alignment['file1_distance'],
                '文件1相对距离': alignment['file1_redis'],
                '文件2环焊缝': alignment['file2_weld'],
                '文件2绝对距离': alignment['file2_distance'],
                '文件2相对距离': alignment['file2_redis'],
                '对齐置信度': alignment['confidence']
            })
        else:
            all_welds.append({
                '类型': '文件1未对齐',
                '文件1环焊缝': alignment['file1_weld'],
                '文件1绝对距离': alignment['file1_distance'],
                '文件1相对距离': alignment['file1_redis'],
                '文件2环焊缝': alignment['file2_weld'],
                '文件2绝对距离': alignment['file2_distance'],
                '文件2相对距离': alignment['file2_redis'],
                '对齐置信度': alignment['confidence']
            })

    return all_welds


def sort_defect_alignment_results(defect_alignment_df: pd.DataFrame) -> pd.DataFrame:
    """
    对缺陷对齐结果按里程排序

    Args:
        defect_alignment_df: 缺陷对齐结果DataFrame

    Returns:
        pd.DataFrame: 排序后的缺陷对齐结果
    """

    # 创建排序键：优先使用文件1绝对距离，如果为空则使用文件2绝对距离
    def get_sort_key(row):
        if row['文件1绝对距离'] != '':
            try:
                return float(row['文件1绝对距离'])
            except:
                return float('inf')
        elif row['文件2绝对距离'] != '':
            try:
                return float(row['文件2绝对距离'])
            except:
                return float('inf')
        else:
            return float('inf')

    # 添加排序键
    sort_keys = defect_alignment_df.apply(get_sort_key, axis=1)

    # 按排序键排序
    sorted_indices = sort_keys.argsort()
    sorted_df = defect_alignment_df.iloc[sorted_indices].reset_index(drop=True)

    return sorted_df


def calculate_base_distances_from_data(rel_dist1: List[float], rel_dist2: List[float]) -> List[float]:
    """
    根据相对距离数据的统计特征计算基础距离值

    Args:
        rel_dist1: 文件1相对距离列表
        rel_dist2: 文件2相对距离列表

    Returns:
        List[float]: 计算得到的基础距离值列表
    """
    # 合并两个文件的相对距离数据
    all_rel_distances = rel_dist1 + rel_dist2

    # 过滤掉0值（起始点的相对距离）
    filtered_distances = [d for d in all_rel_distances if d > 0]

    if not filtered_distances:
        # 如果没有有效数据，返回默认值
        return [10, 50, 100, 200]

    # 计算统计特征
    mean_val = np.mean(filtered_distances)
    median_val = np.median(filtered_distances)
    std_val = np.std(filtered_distances)
    max_val = np.max(filtered_distances)

    print(f"相对距离统计: 均值={mean_val:.2f}, 中位数={median_val:.2f}, 标准差={std_val:.2f}, 最大值={max_val:.2f}")

    # 基于统计特征生成基础距离值
    base_distances = set()

    # 添加基于均值的值
    # base_distances.add(round(mean_val, 1))
    # base_distances.add(round(mean_val * 2, 1))
    # base_distances.add(round(mean_val * 3, 1))

    # 添加基于中位数的值
    # base_distances.add(round(median_val, 1))
    # base_distances.add(round(median_val * 2, 1))
    # base_distances.add(round(median_val * 3, 1))

    # 添加基于标准差的值
    if std_val > 0:
        base_distances.add(round(mean_val + std_val, 1))
        base_distances.add(round(5 * (mean_val + std_val), 1))
        base_distances.add(round(10 * (mean_val + std_val), 1))
        base_distances.add(round(10 * (mean_val + std_val), 1))
        base_distances.add(10)

    # 确保包含一些常用值
    # base_distances.update([10, 20, 50, 100])

    # 过滤掉过大或过小的值
    min_distance = 5  # 最小基础距离
    max_distance = 300  # 最大基础距离

    filtered_base_distances = [math.ceil(d) for d in base_distances if min_distance <= d <= max_distance]

    # 排序并返回前5个值
    filtered_base_distances.sort()
    return filtered_base_distances[:3]


def find_best_weld_alignment(weld_nums1_str, abs_dist1, rel_dist1, weld_nums2_str, abs_dist2, rel_dist2):
    """
    尝试不同的基础距离值，找到环焊缝对齐数最高的结果

    Args:
        weld_nums1_str: 文件1环焊缝编号字符串列表
        abs_dist1: 文件1绝对距离列表
        rel_dist1: 文件1相对距离列表
        weld_nums2_str: 文件2环焊缝编号字符串列表
        abs_dist2: 文件2绝对距离列表
        rel_dist2: 文件2相对距离列表

    Returns:
        tuple: (最佳环焊缝对齐结果, 最佳基础距离值)
    """
    # 根据数据统计特征计算基础距离值
    base_distances = calculate_base_distances_from_data(rel_dist1, rel_dist2)

    best_alignment = None
    best_base_distance = 0
    max_aligned_count = 0

    print("正在尝试不同的基础距离值...")
    print(f"尝试的基础距离值: {base_distances}")

    for base_distance in base_distances:
        print(f"\n尝试基础距离: {base_distance}米")
        weld_alignment = comprehensive_weld_alignment(
            weld_nums1_str, abs_dist1, rel_dist1,
            weld_nums2_str, abs_dist2, rel_dist2,
            base_distance=base_distance,
            similarity_threshold=0.1
        )

        aligned_count = weld_alignment.aligned_count
        print(f"基础距离 {base_distance}米: 对齐 {aligned_count} 对环焊缝")

        if aligned_count > max_aligned_count:
            max_aligned_count = aligned_count
            best_alignment = weld_alignment
            best_base_distance = base_distance

    print(f"\n最佳基础距离: {best_base_distance}米, 对齐 {max_aligned_count} 对环焊缝")

    return best_alignment, best_base_distance


def get_sheet_names(file_path):
    """
    获取Excel文件中的所有工作表名称

    Args:
        file_path: Excel文件路径

    Returns:
        List[str]: 工作表名称列表
    """
    try:
        # 使用ExcelFile获取所有工作表名称
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        return sheet_names
    except Exception as e:
        print(f"获取工作表名称时出错: {e}")
        # 如果出错，返回默认的工作表名称
        return ['Sheet1']


@tool
def pipeline_alignment_tool(filename1: str, filename2: str, threshold: float = 0.06) -> str:
    """
    管道环焊缝与缺陷对齐工具。
    
    功能：
    1. 读取两个 Excel 文件中的环焊缝和缺陷数据。
    2. 基于相对距离算法进行环焊缝对齐。
    3. 基于环焊缝关系进行缺陷匹配。
    4. 生成包含对齐结果和统计信息的 Excel 报告。
    
    Args:
        filename1 (str): 第一个 Excel 文件名（如 "1.xlsx"）。需包含 "Pipeline Listing" Sheet。
        filename2 (str): 第二个 Excel 文件名（如 "2.xlsx"）。需包含 "管道列表" Sheet。
        threshold (float): 对齐匹配的误差阈值，默认为 0.2。
        
    Returns:
        str: 执行结果报告，包含下载链接协议 [FILE:xxx]。
    """
    base_dir = os.path.join(os.getcwd(), "UploadedFiles")
    output_dir = os.path.join(os.getcwd(), "GeneratedFiles")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file1_path = os.path.join(base_dir, os.path.basename(filename1))
    file2_path = os.path.join(base_dir, os.path.basename(filename2))

    output_filename = f"aligned_{os.path.splitext(os.path.basename(filename1))[0]}_{os.path.splitext(os.path.basename(filename2))[0]}.xlsx"
    output_path = os.path.join(output_dir, output_filename)

    # 2. 检查文件
    if not os.path.exists(file1_path): return f"错误：找不到文件 {filename1}"
    if not os.path.exists(file2_path): return f"错误：找不到文件 {filename2}"

    try:
        print("正在读取文件1...")
        # 获取文件1的工作表名称
        sheet_names1 = get_sheet_names(file1_path)
        print(f"文件1的工作表: {sheet_names1}")
        # 使用第一个工作表
        df1 = pd.read_excel(file1_path, sheet_name=sheet_names1[0])

        print("正在读取文件2...")
        # 获取文件2的工作表名称
        sheet_names2 = get_sheet_names(file2_path)
        print(f"文件2的工作表: {sheet_names2}")
        # 使用第一个工作表
        df2 = pd.read_excel(file2_path, sheet_name=sheet_names2[0])

        # 读取环焊缝数据
        print("正在提取环焊缝数据...")
        abs_dist1, rel_dist1, weld_nums1 = read_weld_data(df1)
        abs_dist2, rel_dist2, weld_nums2 = read_weld_data(df2)

        # 转换为字符串列表
        weld_nums1_str = [str(w) for w in weld_nums1]
        weld_nums2_str = [str(w) for w in weld_nums2]

        print(f"文件1: 找到 {len(abs_dist1)} 个环焊缝")
        print(f"文件2: 找到 {len(abs_dist2)} 个环焊缝")

        # 尝试不同的基础距离值，找到最佳环焊缝对齐结果
        print("正在进行环焊缝对齐...")
        weld_alignment, best_base_distance = find_best_weld_alignment(
            weld_nums1_str, abs_dist1, rel_dist1,
            weld_nums2_str, abs_dist2, rel_dist2
        )

        # 统计对齐结果
        aligned_count = weld_alignment.aligned_count
        file1_only_count = sum(1 for a in weld_alignment.alignments
                               if a['file1_weld'] != ' ' and a['file2_weld'] == ' ')
        file2_only_count = sum(1 for a in weld_alignment.alignments
                               if a['file1_weld'] == ' ' and a['file2_weld'] != ' ')

        print(f"使用最佳基础距离 {best_base_distance}米")
        print(f"成功对齐 {aligned_count} 对环焊缝")
        print(f"文件1中未匹配的环焊缝: {file1_only_count}")
        print(f"文件2中未匹配的环焊缝: {file2_only_count}")

        # 读取缺陷数据 - 使用统一的函数
        print("正在提取缺陷数据...")
        defects1 = read_defect_data(df1, file_type=1)
        defects2 = read_defect_data(df2, file_type=2)

        print(f"文件1: 找到 {len(defects1)} 个缺陷")
        print(f"文件2: 找到 {len(defects2)} 个缺陷")

        # 使用最佳环焊缝对齐结果进行缺陷对齐
        print("正在进行缺陷对齐...")
        defect_alignment_df = align_defects_with_comprehensive_mapping(defects1, defects2, weld_alignment)

        # 对结果进行排序
        print("正在对结果进行排序...")
        # 排序环焊缝对齐结果
        sorted_weld_alignment = sort_weld_alignment_results(weld_alignment)
        # 排序缺陷对齐结果
        sorted_defect_alignment = sort_defect_alignment_results(defect_alignment_df)

        # 统计匹配结果
        exact_matches = len(sorted_defect_alignment[
                                (sorted_defect_alignment['匹配类型'] == '环焊缝对齐匹配')
                            ])
        relative_matches = len(sorted_defect_alignment[
                                   (sorted_defect_alignment['匹配类型'] == '相对距离匹配')
                               ])
        total_matches = exact_matches + relative_matches

        print(f"环焊缝对齐匹配: {exact_matches} 对缺陷")
        print(f"相对距离匹配: {relative_matches} 对缺陷")
        print(f"总匹配: {total_matches} 对缺陷")

        # 保存结果
        print("正在保存结果...")
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # 保存排序后的环焊缝对齐结果
            weld_alignment_df = pd.DataFrame(sorted_weld_alignment)
            weld_alignment_df.to_excel(writer, sheet_name='环焊缝对齐', index=False)

            # 保存排序后的缺陷对齐结果
            sorted_defect_alignment.to_excel(writer, sheet_name='缺陷对齐结果', index=False)

            # 添加数据统计
            stats_data = {
                '统计项': [
                    '文件1环焊缝数', '文件2环焊缝数', '成功对齐数',
                    '文件1未匹配环焊缝数', '文件2未匹配环焊缝数',
                    '文件1缺陷数', '文件2缺陷数',
                    '环焊缝对齐匹配数', '相对距离匹配数', '总匹配数',
                    '最佳基础距离'
                ],
                '数量': [
                    len(weld_alignment.get_all_file1_welds()),
                    len(weld_alignment.get_all_file2_welds()),
                    aligned_count,
                    file1_only_count,
                    file2_only_count,
                    len(defects1), len(defects2),
                    exact_matches, relative_matches, total_matches,
                    best_base_distance
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='数据统计', index=False)

            # 添加匹配类型统计
            match_type_stats = sorted_defect_alignment['匹配类型'].value_counts().reset_index()
            match_type_stats.columns = ['匹配类型', '数量']
            match_type_stats.to_excel(writer, sheet_name='匹配类型统计', index=False)

        print(f"对齐完成！结果已保存到: {output_path}")

        return (f"✅ 对齐完成！\n"
                f"- 环焊缝对齐数: {len(weld_alignment.alignments)}\n"
                f"- 缺陷匹配数: {total_matches}\n"
                f"结果已保存，请下载: [FILE:{output_filename}]")

    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ 对齐算法执行出错: {str(e)}\n{traceback.format_exc()}"

