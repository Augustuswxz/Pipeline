import chromadb
import uuid
import os
import json  # 必须导入 json 用于序列化列表

class AlignmentMemory:
    def __init__(self, persist_path="KnowledgeBase/align_memory_db"):
        """
        初始化对齐记忆库
        """
        base_dir = os.getcwd()
        full_path = os.path.join(base_dir, persist_path)
        
        self.client = chromadb.PersistentClient(path=full_path)
        self.collection_name = "alignment_history"
        
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"} 
        )

    def search_similar(self, vector_a: list, threshold=0.3):
        """
        根据向量 A 寻找相似的历史记录
        """
        if not vector_a:
            return None

        try:
            results = self.collection.query(
                query_embeddings=[vector_a],
                n_results=1, 
                include=["metadatas", "distances"]
            )
        except Exception as e:
            print(f"[查询错误] 可能是维度不匹配: {e}")
            return None

        if not results['ids'] or len(results['ids'][0]) == 0:
            return None
        
        distance = results['distances'][0][0]
        if distance > threshold:
            print(f"[记忆检索] 最相似距离 {distance:.4f} > 阈值 {threshold}，判定为无相似。")
            return None

        # 提取数据
        record_id = results['ids'][0][0]
        metadata = results['metadatas'][0][0]
        
        print(f"[记忆检索] ✅ 命中历史! ID: {record_id}, 距离: {distance:.4f}")

        # --- 修改点 1: 反序列化 ---
        # 从 metadata 字符串中还原回 List
        b_val_str = metadata.get("system_val", "[]")
        c_val_str = metadata.get("expert_val", "[]")

        return {
            "id": record_id,
            "b_value": json.loads(b_val_str),      # 还原为 5维向量
            "c_value": json.loads(c_val_str),      # 还原为 5维向量
            "c_comment": metadata.get("expert_comment")
        }

    def add_record(self, vector_a: list, system_val: list, expert_val: list = None, comment: str = ""):
        """
        新增一条记录
        :param system_val: 5维向量 (List[float])
        :param expert_val: 5维向量 (List[float])，如为空则默认等于 system_val
        """
        # 确保 expert_val 有值
        if expert_val is None:
            expert_val = system_val

        # --- 修改点 2: 序列化 ---
        # ChromaDB metadata 不支持直接存 List，必须转为 JSON 字符串
        metadata = {
            "system_val": json.dumps(system_val), # 存为字符串 "[1.1, 2.2, ...]"
            "expert_val": json.dumps(expert_val), 
            "expert_comment": comment
        }
        
        record_id = str(uuid.uuid4())
        
        self.collection.add(
            embeddings=[vector_a],
            metadatas=[metadata],
            ids=[record_id]
        )
        print(f"[记忆保存] 已保存记录 ID: {record_id}")
        return record_id

    def update_expert_feedback(self, record_id: str, expert_val: list, comment: str = "专家修正"):
        """
        更新专家反馈 (更新字段 C)
        :param expert_val: 新的 5维向量
        """
        existing = self.collection.get(ids=[record_id], include=['metadatas'])
        if not existing['ids']:
            return "❌ 记录不存在"
            
        current_meta = existing['metadatas'][0]
        
        # --- 修改点 3: 更新时的序列化 ---
        current_meta['expert_val'] = json.dumps(expert_val) # 更新为新的向量字符串
        current_meta['expert_comment'] = comment
        
        self.collection.update(
            ids=[record_id],
            metadatas=[current_meta]
        )
        print(f"[记忆更新] 已更新专家数据 ID: {record_id}")
        return "专家经验已更新"

    def peek_current_status(self):
        count = self.collection.count()
        print(f"当前集合 '{self.collection_name}' 中共有 {count} 条数据。")
        if count > 0:
            print("预览前1条数据:", self.collection.peek(limit=1))
    
    def reset_collection(self):
        print(f"正在删除集合: {self.collection_name} ...")
        try:
            self.client.delete_collection(self.collection_name)
            print("✅ 旧集合已删除。")
        except Exception as e:
            print(f"删除集合时提示: {e}")

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"} 
        )
        print("✅ 新集合已创建 (空)。")


# --- 测试主函数 ---
if __name__ == "__main__":
    db = AlignmentMemory()
    
    print("\n========= 1. 重置库 (为了测试新结构) =========")
    db.reset_collection()
    
    print("\n========= 2. 存入新的记录 (全都是向量) =========")
    # 1. 用于检索的向量 (5维)
    search_vector = [
        4.6, 19.2, 9851.3, 0.03, 0.56
    ]
    
    # 2. 系统计算出的配置参数 (也是5维向量)
    sys_config_vector = [0.1, 0.2, 0.3, 0.4, 0.5]

    # 3. 专家修改后的配置参数 (也是5维向量)
    exp_config_vector = [1.0, 45, 10, 10, 2]
    
    print(f"检索向量: {search_vector}")
    print(f"系统参数: {sys_config_vector}")
    print(f"专家参数: {exp_config_vector}")

    # 存入
    rec_id = db.add_record(
        vector_a=search_vector, 
        system_val=sys_config_vector,  # 传入 List
        expert_val=exp_config_vector,  # 传入 List
        comment="5维向量全量测试"
    )
    
    print("\n========= 3. 验证查询 =========")
    match = db.search_similar(search_vector, threshold=0.001)
    
    if match:
        print("✅ 测试成功！数据已读出：")
        print(f"ID: {match['id']}")
        print(f"系统值 (type {type(match['b_value'])}): {match['b_value']}")
        print(f"专家值 (type {type(match['c_value'])}): {match['c_value']}")
        print(f"备注: {match['c_comment']}")
    else:
        print("❌ 测试失败：未查找到数据。")

    print("\n========= 4. 测试更新专家向量 =========")
    # 假设专家又改了一次
    new_expert_vector = [1.1, 46, 11, 11, 3]
    db.update_expert_feedback(rec_id, new_expert_vector, comment="专家二次修正")
    
    # 再次查询验证
    match_updated = db.search_similar(search_vector)
    print(f"更新后专家值: {match_updated['c_value']}")