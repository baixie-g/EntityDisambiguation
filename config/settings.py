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
    HIGH_THRESHOLD: float = 0.85  # 高于此阈值直接合并
    LOW_THRESHOLD: float = 0.65   # 低于此阈值直接新建
    
    # 向量检索配置
    FAISS_TOP_K: int = 10
    CROSS_ENCODER_TOP_K: int = 5
    
    # 权重配置
    BGE_WEIGHT: float = 0.4
    CROSS_ENCODER_WEIGHT: float = 0.3
    FUZZ_WEIGHT: float = 0.2
    LEVENSHTEIN_WEIGHT: float = 0.1
    
    # SQLite数据库配置（专门用于历史记录）
    SQLITE_DATABASE_PATH: str = "data/disambiguation_history.db"
    FAISS_INDEX_PATH: str = "data/faiss_index"
    
    # Neo4j数据库配置（专门用于实体存储）
    # NEO4J_URI: str = "bolt://47.105.115.60:7687"
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