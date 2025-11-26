import chromadb
import uuid
import os
import json

class AlignmentMemory:
    def __init__(self, persist_path="KnowledgeBase/align_memory_db"):
        """
        初始化对齐记忆库
        :param persist_path: 数据库保存的本地文件夹路径
        """
        # 获取当前脚本的绝对路径，确保数据库存在项目目录下
        base_dir = os.getcwd()
        full_path = os.path.join(base_dir, persist_path)
        
        # 初始化持久化客户端 (数据会保存在硬盘上)
        self.client = chromadb.PersistentClient(path=full_path)
        
        # 获取或创建集合 (Collection)
        # 这里的 metadata 指定了距离算法，"cosine" 表示余弦相似度
        self.collection = self.client.get_or_create_collection(
            name="alignment_history",
            metadata={"hnsw:space": "cosine"} 
        )

    def search_similar(self, vector_a: list, threshold=0.3):
        """
        根据向量 A 寻找相似的历史记录
        :param vector_a: 当前文件的特征向量 (List[float])
        :param threshold: 相似度阈值 (余弦距离，越小越相似。0=完全一样)
        :return: 匹配到的字典 或 None
        """
        if not vector_a:
            return None

        # 查询 Chroma
        results = self.collection.query(
            query_embeddings=[vector_a],
            n_results=1, # 只取最相似的1个
            include=["metadatas", "distances"]
        )

        # 检查是否有结果
        if not results['ids'] or len(results['ids'][0]) == 0:
            return None
        
        # 检查阈值 (distance 越小越相似)
        distance = results['distances'][0][0]
        if distance > threshold:
            print(f"[记忆检索] 最相似距离 {distance:.4f} > 阈值 {threshold}，判定为无相似。")
            return None

        # 提取数据
        record_id = results['ids'][0][0]
        metadata = results['metadatas'][0][0]
        
        print(f"[记忆检索] ✅ 命中历史! ID: {record_id}, 距离: {distance:.4f}")

        return {
            "id": record_id,
            "b_value": metadata.get("system_val"),       # 字段 B
            "c_value": metadata.get("expert_val"),       # 字段 C (数值)
            "c_comment": metadata.get("expert_comment")  # 字段 C (自然语言)
        }

    def add_record(self, vector_a: list, system_val: float, expert_val: float = None, comment: str = ""):
        """
        新增一条记录
        :param vector_a: 向量 A
        :param system_val: 系统计算结果 (字段 B)
        :param expert_val: 专家调整结果 (字段 C 的数值，可选)
        :param comment: 专家说明 (字段 C 的文本，可选)
        """
        # 构造元数据 (存放字段 B 和 C)
        metadata = {
            "system_val": float(system_val),
            # 如果没有专家值，默认初始化为 None 或与 system_val 相同，看你业务需求
            # 这里为了后续逻辑方便，如果没专家值，存 None
            "expert_val": float(expert_val) if expert_val is not None else system_val, 
            "expert_comment": comment
        }
        
        # 生成唯一 ID
        record_id = str(uuid.uuid4())
        
        self.collection.add(
            embeddings=[vector_a],
            metadatas=[metadata],
            ids=[record_id]
        )
        print(f"[记忆保存] 已保存记录 ID: {record_id}")
        return record_id

    def update_expert_feedback(self, record_id: str, expert_val: float, comment: str = "专家修正"):
        """
        更新专家反馈 (更新字段 C)
        """
        # 1. 先读取旧数据
        existing = self.collection.get(ids=[record_id], include=['metadatas'])
        if not existing['ids']:
            return "❌ 记录不存在"
            
        # 2. 修改 Metadata
        current_meta = existing['metadatas'][0]
        current_meta['expert_val'] = float(expert_val)
        current_meta['expert_comment'] = comment
        
        # 3. 更新回数据库
        self.collection.update(
            ids=[record_id],
            metadatas=[current_meta]
        )
        print(f"[记忆更新] 已更新专家数据 ID: {record_id}")
        return "专家经验已更新"

# --- 测试代码 (你可以直接运行这个文件测试) ---
if __name__ == "__main__":
    db = AlignmentMemory()
    
    # 模拟向量 (假设是 3 维)
    vec1 = [0.1, 0.2, 0.3]
    
    # 1. 添加
    rid = db.add_record(vec1, system_val=0.5)
    
    # 2. 查询
    res = db.search_similar([0.1, 0.21, 0.3]) # 稍微有一点点偏差的向量
    print("查询结果:", res)
    
    # 3. 更新
    if res:
        db.update_expert_feedback(res['id'], expert_val=0.8, comment="太小了，调大点")
        
    # 4. 再次查询
    res2 = db.search_similar([0.1, 0.2, 0.3])
    print("更新后查询:", res2)