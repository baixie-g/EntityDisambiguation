"""
实体消歧服务配置文件
"""
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # 模型配置
    # BGE_MODEL_NAME: str = "BAAI/bge-m3"
    BGE_MODEL_NAME: str = "BAAI/bge-m3"
    CROSS_ENCODER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    # 相似度阈值
    HIGH_THRESHOLD: float = 0.72  # 高于此阈值直接合并
    LOW_THRESHOLD: float = 0.6    # 低于此阈值直接新建
    
    # 向量检索配置
    FAISS_TOP_K: int = 10
    CROSS_ENCODER_TOP_K: int = 5
    


#     ================================================================================
# 总结
# ================================================================================
# 📈 得分范围总结:
#   1. 各模型得分范围: 0.0 - 1.0
#   2. 加权得分范围: 0.0 - 1.0
#   3. 最终得分范围:
#      - 类型匹配: 0.0 - 1.0
#      - 类型不匹配: 0.0 - 0.1
#      - 类型缺失: 0.0 - 1.0

# ⚠️ 当前配置问题:
#   - 类型不匹配惩罚过重: 0.1倍
#   - 高阈值过高: 1.0
#   - 低阈值过高: 0.5

# 🔧 建议调整:
#   TYPE_MISMATCH_PENALTY: 0.1 → 0.3
#   TYPE_MATCH_BONUS: 1.0 → 1.1
#   HIGH_THRESHOLD: 1.0 → 0.85
#   LOW_THRESHOLD: 0.5 → 0.3


# 最终得分 = (BGE得分 × 0.4 + CrossEncoder得分 × 0.3 + Fuzz得分 × 0.2 + Levenshtein得分 × 0.1) × 类型匹配倍数

    # 权重配置 - 用于计算综合相似度得分
    # 最终得分计算公式：
    # final_score = (bge_score * BGE_WEIGHT + cross_encoder_score * CROSS_ENCODER_WEIGHT + 
    #                fuzz_score * FUZZ_WEIGHT + levenshtein_score * LEVENSHTEIN_WEIGHT) * type_multiplier
    # 其中 type_multiplier 根据实体类型匹配情况确定：
    # - 类型匹配: type_multiplier = TYPE_MATCH_BONUS (1.1)
    # - 类型不匹配: type_multiplier = TYPE_MISMATCH_PENALTY (0.3)
    # - 类型信息缺失: type_multiplier = 1.0 (无影响)
    BGE_WEIGHT: float = 0.4        # BGE-M3向量相似度权重 (40%)
    CROSS_ENCODER_WEIGHT: float = 0.3  # CrossEncoder重排序权重 (30%，已线性归一化到0.0-1.0)
    FUZZ_WEIGHT: float = 0.2       # RapidFuzz字符串匹配权重 (20%)
    LEVENSHTEIN_WEIGHT: float = 0.1    # Levenshtein编辑距离权重 (10%)

    # 类型匹配权重 - 当实体类型不同时使用的惩罚权重
    # 这些权重用于在最终得分计算中应用类型匹配的影响
    # 计算公式中的 type_multiplier 参数：
    TYPE_MISMATCH_PENALTY: float = 0.1  # 类型不匹配时，最终得分乘以0.1 (降低90%)
    TYPE_MATCH_BONUS: float = 1       # 类型匹配时，最终得分乘以1 (提升10%)
    
    # SQLite数据库配置（专门用于历史记录）
    SQLITE_DATABASE_PATH: str = "data/disambiguation_history.db"
    FAISS_INDEX_PATH: str = "data/faiss_index"
    
    # Neo4j数据库配置（专门用于实体存储）
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "12345678"
    NEO4J_DATABASE: str = "neo4j"  # 数据库名称
    
    # 向量维度
    EMBEDDING_DIM: int = 1024
    
    # 服务配置
    HOST: str = "localhost"
    PORT: int = 8002
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"

settings = Settings() 