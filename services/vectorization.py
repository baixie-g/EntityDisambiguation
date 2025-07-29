"""
向量化和FAISS索引服务
"""
import numpy as np
import faiss
import pickle
import logging
from typing import List, Tuple, Optional, Dict, Any, Union
from pathlib import Path
import torch
from sentence_transformers import SentenceTransformer

from models import Entity, CandidateMatch, EntityScore
from config.settings import settings

logger = logging.getLogger(__name__)

# 尝试导入BGE-M3模型
try:
    from FlagEmbedding import BGEM3FlagModel
    BGE_M3_AVAILABLE = True
except ImportError:
    BGE_M3_AVAILABLE = False
    logger.warning("FlagEmbedding未安装，将使用sentence-transformers作为备选")

class VectorizationService:
    """向量化服务类"""
    
    def __init__(self):
        self.bge_model: Optional[Union[SentenceTransformer, Any]] = None
        self.faiss_index: Optional[faiss.Index] = None
        self.entity_id_mapping: Dict[int, str] = {}  # 索引位置到实体ID的映射
        self.model_loaded = False
        self.index_loaded = False
        
        # 延迟导入数据库管理器以避免循环导入
        self.db_manager = None
    
    def _get_db_manager(self):
        """获取数据库管理器实例"""
        if self.db_manager is None:
            from .database_factory import db_manager
            self.db_manager = db_manager
        return self.db_manager
    
    def load_bge_model(self):
        """加载BGE-M3模型"""
        if self.model_loaded:
            return
            
        try:
            if BGE_M3_AVAILABLE:
                logger.info(f"加载BGE-M3模型: {settings.BGE_MODEL_NAME}")
                self.bge_model = BGEM3FlagModel(settings.BGE_MODEL_NAME, use_fp16=True)
                self.model_loaded = True
                logger.info("BGE-M3模型加载成功")
            else:
                raise ImportError("FlagEmbedding不可用")
        except Exception as e:
            logger.error(f"加载BGE-M3模型失败: {e}")
            # 降级使用sentence-transformers
            try:
                logger.info("尝试使用sentence-transformers加载模型")
                self.bge_model = SentenceTransformer(settings.BGE_MODEL_NAME)
                self.model_loaded = True
                logger.info("句子变换器模型加载成功")
            except Exception as e2:
                logger.error(f"加载句子变换器模型失败: {e2}")
                raise e2
    
    def encode_entity(self, entity: Entity) -> np.ndarray:
        """编码实体"""
        if not self.model_loaded:
            self.load_bge_model()
        
        if self.bge_model is None:
            logger.error("模型未加载")
            return np.zeros(settings.EMBEDDING_DIM)
        
        try:
            # 构建实体文本
            text_parts = [entity.name]
            
            # 添加别名
            if entity.aliases:
                text_parts.extend(entity.aliases)
            
            # 添加定义
            if entity.definition:
                text_parts.append(entity.definition)
            
            # 添加属性信息
            if entity.attributes:
                for key, value in entity.attributes.items():
                    if isinstance(value, list):
                        text_parts.append(f"{key}: {', '.join(str(v) for v in value)}")
                    else:
                        text_parts.append(f"{key}: {value}")
            
            # 合并所有文本
            full_text = " ".join(text_parts)
            
            # 编码
            if BGE_M3_AVAILABLE and hasattr(self.bge_model, 'encode'):
                # 使用BGE-M3模型
                embeddings = self.bge_model.encode([full_text])
                if isinstance(embeddings, dict) and 'dense_vecs' in embeddings:
                    return np.array(embeddings['dense_vecs'][0])
                else:
                    return np.array(embeddings[0])
            else:
                # 使用sentence-transformers
                embedding = self.bge_model.encode([full_text])
                return np.array(embedding[0])
                
        except Exception as e:
            logger.error(f"编码实体失败: {e}")
            # 返回零向量
            return np.zeros(settings.EMBEDDING_DIM)
    
    def build_faiss_index(self, entities: List[Entity]) -> bool:
        """构建FAISS索引"""
        try:
            if not self.model_loaded:
                self.load_bge_model()
            
            logger.info(f"开始构建FAISS索引，实体数量: {len(entities)}")
            
            # 编码所有实体
            vectors = []
            entity_ids = []
            
            for i, entity in enumerate(entities):
                vector = self.encode_entity(entity)
                vectors.append(vector)
                entity_ids.append(entity.id or f"entity_{i}")
                
                if i % 100 == 0:
                    logger.info(f"已编码 {i+1}/{len(entities)} 个实体")
            
            if not vectors:
                logger.warning("没有向量可用于构建索引")
                return False
            
            # 转换为numpy数组
            vectors_array = np.array(vectors).astype('float32')
            
            # 构建FAISS索引
            dimension = vectors_array.shape[1]
            self.faiss_index = faiss.IndexFlatIP(dimension)  # 使用内积相似度
            
            # 添加向量到索引
            self.faiss_index.add(vectors_array)
            
            # 保存实体ID映射
            self.entity_id_mapping = {i: entity_id for i, entity_id in enumerate(entity_ids)}
            
            # 保存索引和映射
            self.save_index()
            
            logger.info(f"FAISS索引构建完成，维度: {dimension}, 向量数量: {len(vectors)}")
            self.index_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"构建FAISS索引失败: {e}")
            return False
    
    def save_index(self):
        """保存FAISS索引"""
        try:
            if self.faiss_index is None:
                logger.error("索引为空，无法保存")
                return
                
            # 确保目录存在
            Path(settings.FAISS_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存FAISS索引
            faiss.write_index(self.faiss_index, f"{settings.FAISS_INDEX_PATH}.index")
            
            # 保存实体ID映射
            with open(f"{settings.FAISS_INDEX_PATH}.mapping", 'wb') as f:
                pickle.dump(self.entity_id_mapping, f)
            
            logger.info("FAISS索引保存成功")
            
        except Exception as e:
            logger.error(f"保存FAISS索引失败: {e}")
    
    def load_index(self) -> bool:
        """加载FAISS索引"""
        try:
            index_file = f"{settings.FAISS_INDEX_PATH}.index"
            mapping_file = f"{settings.FAISS_INDEX_PATH}.mapping"
            
            if not Path(index_file).exists() or not Path(mapping_file).exists():
                logger.warning("FAISS索引文件不存在，需要重新构建")
                return False
            
            # 加载FAISS索引
            self.faiss_index = faiss.read_index(index_file)
            
            # 加载实体ID映射
            with open(mapping_file, 'rb') as f:
                self.entity_id_mapping = pickle.load(f)
            
            logger.info("FAISS索引加载成功")
            self.index_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"加载FAISS索引失败: {e}")
            return False
    
    def search_similar_entities(self, query_entity: Entity, top_k: Optional[int] = None) -> List[Tuple[Entity, float]]:
        """搜索相似实体"""
        try:
            if not self.index_loaded:
                if not self.load_index():
                    logger.warning("索引未加载，尝试重新构建")
                    entities = self._get_db_manager().get_all_entities()
                    if not self.build_faiss_index(entities):
                        logger.error("无法构建索引")
                        return []
            
            if not self.model_loaded:
                self.load_bge_model()
            
            if self.faiss_index is None:
                logger.error("索引为空")
                return []
            
            # 编码查询实体
            query_vector = self.encode_entity(query_entity)
            query_vector = query_vector.reshape(1, -1).astype('float32')
            
            # 搜索相似向量
            k = top_k or settings.FAISS_TOP_K
            scores, indices = self.faiss_index.search(query_vector, k)
            
            # 获取相似实体
            similar_entities = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # 无效索引
                    continue
                    
                entity_id = self.entity_id_mapping.get(idx)
                if entity_id:
                    entity = self._get_db_manager().get_entity(entity_id)
                    if entity:
                        similar_entities.append((entity, float(score)))
            
            return similar_entities
            
        except Exception as e:
            logger.error(f"搜索相似实体失败: {e}")
            return []
    
    def get_entity_vector(self, entity: Entity) -> Optional[np.ndarray]:
        """获取实体向量"""
        try:
            if not self.model_loaded:
                self.load_bge_model()
            
            return self.encode_entity(entity)
            
        except Exception as e:
            logger.error(f"获取实体向量失败: {e}")
            return None
    
    def rebuild_index(self) -> bool:
        """重建索引"""
        try:
            logger.info("开始重建FAISS索引")
            entities = self._get_db_manager().get_all_entities()
            
            if not entities:
                logger.warning("没有实体可用于构建索引")
                return False
            
            return self.build_faiss_index(entities)
            
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False
    
    def add_entity_to_index(self, entity: Entity) -> bool:
        """添加实体到索引"""
        try:
            if not self.index_loaded:
                if not self.load_index():
                    logger.warning("索引未加载，无法添加实体")
                    return False
            
            if self.faiss_index is None:
                logger.error("索引为空")
                return False
            
            # 编码实体
            vector = self.encode_entity(entity)
            vector = vector.reshape(1, -1).astype('float32')
            
            # 添加到索引
            next_id = len(self.entity_id_mapping)
            self.faiss_index.add(vector)
            self.entity_id_mapping[next_id] = entity.id or f"entity_{next_id}"
            
            # 保存更新的索引
            self.save_index()
            
            logger.info(f"实体 {entity.id} 添加到索引成功")
            return True
            
        except Exception as e:
            logger.error(f"添加实体到索引失败: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        stats = {
            "model_loaded": self.model_loaded,
            "index_loaded": self.index_loaded,
            "entity_count": len(self.entity_id_mapping) if self.entity_id_mapping else 0,
            "index_dimension": self.faiss_index.d if self.faiss_index else 0
        }
        return stats

# 全局向量化服务实例
vectorization_service = VectorizationService()