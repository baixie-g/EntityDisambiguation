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
import os
import json

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
        self.device = None
        self.gpu_available = False
        
        # 延迟导入数据库管理器以避免循环导入
        self.db_manager = None
    
    def _get_db_manager(self):
        """获取数据库管理器实例"""
        if self.db_manager is None:
            from .database_factory import db_manager
            self.db_manager = db_manager
        return self.db_manager
    
    def _detect_gpu(self) -> bool:
        """检测GPU可用性"""
        try:
            # 检查CUDA是否可用
            if not torch.cuda.is_available():
                logger.info("PyTorch CUDA不可用，将使用CPU")
                self.device = torch.device('cpu')
                return False
            
            # 检查GPU数量
            gpu_count = torch.cuda.device_count()
            if gpu_count == 0:
                logger.info("未检测到GPU设备，将使用CPU")
                self.device = torch.device('cpu')
                return False
            
            # 获取第一个GPU的信息
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            
            logger.info(f"检测到GPU: {gpu_name}")
            logger.info(f"GPU内存: {gpu_memory:.1f}GB")
            logger.info(f"GPU数量: {gpu_count}")
            
            # 设置默认GPU设备
            torch.cuda.set_device(0)
            self.device = torch.device('cuda:0')
            
            # 测试GPU是否真正可用
            try:
                test_tensor = torch.tensor([1.0], device=self.device)
                result = test_tensor * 2
                logger.info("GPU测试成功")
                return True
            except Exception as gpu_test_error:
                logger.warning(f"GPU测试失败: {gpu_test_error}")
                self.device = torch.device('cpu')
                return False
                
        except Exception as e:
            logger.warning(f"GPU检测失败: {e}")
            self.device = torch.device('cpu')
            return False
    
    def _check_nvidia_prime_status(self) -> str:
        """检查NVIDIA Prime状态"""
        try:
            import subprocess
            result = subprocess.run(['prime-select', 'query'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "unknown"
        except Exception as e:
            logger.debug(f"检查Prime状态失败: {e}")
            return "unknown"
    
    def _try_enable_gpu(self) -> bool:
        """尝试启用GPU"""
        try:
            # 检查Prime状态
            prime_status = self._check_nvidia_prime_status()
            logger.info(f"NVIDIA Prime状态: {prime_status}")
            
            if prime_status == "on-demand":
                logger.warning("检测到on-demand模式，GPU可能不可用")
                logger.info("建议运行: sudo prime-select nvidia 然后重启系统")
                return False
            elif prime_status == "nvidia":
                logger.info("NVIDIA专用模式已启用")
                # 尝试重新检测GPU
                return self._detect_gpu()
            else:
                logger.info(f"Prime状态: {prime_status}")
                return self._detect_gpu()
                
        except Exception as e:
            logger.warning(f"尝试启用GPU失败: {e}")
            return False
    
    def _find_valid_model_cache(self, model_name: str) -> Optional[str]:
        """查找有效的本地模型缓存"""
        try:
            # 构建缓存路径
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            
            # 尝试多种可能的模型目录名称
            possible_names = [
                f"models--{model_name.replace('/', '--')}",
                f"models--{model_name.replace('/', '--').lower()}",
                model_name.replace('/', '_'),
                model_name.replace('/', '-')
            ]
            
            for name in possible_names:
                model_dir = cache_dir / name
                if not model_dir.exists():
                    continue
                
                logger.info(f"发现模型目录: {model_dir}")
                
                # 检查snapshots目录
                snapshots_dir = model_dir / "snapshots"
                if snapshots_dir.exists():
                    snapshots = list(snapshots_dir.iterdir())
                    if snapshots:
                        # 按修改时间排序，取最新的
                        latest_snapshot = max(snapshots, key=lambda x: x.stat().st_mtime)
                        model_path = str(latest_snapshot)
                        
                        # 验证模型文件是否完整
                        if self._validate_model_files(model_path):
                            logger.info(f"找到有效的本地模型缓存: {model_path}")
                            return model_path
                        else:
                            logger.warning(f"模型文件不完整: {model_path}")
                
                # 检查refs目录
                refs_dir = model_dir / "refs"
                if refs_dir.exists():
                    for ref_file in refs_dir.iterdir():
                        if ref_file.is_file():
                            with open(ref_file, 'r') as f:
                                commit_hash = f.read().strip()
                            model_path = str(model_dir / "snapshots" / commit_hash)
                            if Path(model_path).exists() and self._validate_model_files(model_path):
                                logger.info(f"找到有效的本地模型缓存: {model_path}")
                                return model_path
            
            logger.info("未找到有效的本地模型缓存")
            return None
            
        except Exception as e:
            logger.error(f"查找模型缓存失败: {e}")
            return None
    
    def _validate_model_files(self, model_path: str) -> bool:
        """验证模型文件是否完整"""
        try:
            required_files = ['config.json', 'pytorch_model.bin']
            model_path_obj = Path(model_path)
            
            for file_name in required_files:
                file_path = model_path_obj / file_name
                if not file_path.exists():
                    logger.debug(f"缺少模型文件: {file_path}")
                    return False
            
            # 检查config.json是否有效
            config_file = model_path_obj / 'config.json'
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if not config:
                    logger.debug("config.json为空")
                    return False
            except Exception as e:
                logger.debug(f"config.json解析失败: {e}")
                return False
            
            logger.debug(f"模型文件验证通过: {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"验证模型文件失败: {e}")
            return False
    
    def load_bge_model(self):
        """加载BGE-M3模型"""
        if self.model_loaded:
            return
            
        try:
            # 尝试启用GPU
            self.gpu_available = self._try_enable_gpu()
            
            if BGE_M3_AVAILABLE:
                logger.info(f"加载BGE-M3模型: {settings.BGE_MODEL_NAME}")
                
                # 优先使用本地缓存
                local_model_path = self._find_valid_model_cache(settings.BGE_MODEL_NAME)
                
                if local_model_path:
                    try:
                        logger.info(f"使用本地模型缓存: {local_model_path}")
                        if self.gpu_available:
                            self.bge_model = BGEM3FlagModel(local_model_path, use_fp16=True)
                            logger.info("BGE-M3模型加载成功 (GPU模式，本地缓存)")
                        else:
                            self.bge_model = BGEM3FlagModel(local_model_path, use_fp16=False)
                            logger.info("BGE-M3模型加载成功 (CPU模式，本地缓存)")
                        self.model_loaded = True
                        return
                    except Exception as cache_error:
                        logger.warning(f"本地缓存加载失败: {cache_error}")
                        logger.info("尝试从网络下载模型")
                
                # 如果本地缓存不存在或加载失败，尝试从网络下载
                logger.info("从网络下载BGE-M3模型")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger.info(f"尝试加载BGE-M3模型 (第{attempt + 1}次)")
                        if self.gpu_available:
                            self.bge_model = BGEM3FlagModel(settings.BGE_MODEL_NAME, use_fp16=True)
                            logger.info("BGE-M3模型加载成功 (GPU模式)")
                        else:
                            self.bge_model = BGEM3FlagModel(settings.BGE_MODEL_NAME, use_fp16=False)
                            logger.info("BGE-M3模型加载成功 (CPU模式)")
                        self.model_loaded = True
                        return
                    except Exception as e:
                        logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(5)  # 等待5秒后重试
                        else:
                            raise e
            else:
                raise ImportError("FlagEmbedding不可用")
        except Exception as e:
            logger.error(f"加载BGE-M3模型失败: {e}")
            # 降级使用sentence-transformers
            try:
                logger.info("尝试使用sentence-transformers加载模型")
                
                # 优先使用本地缓存
                local_model_path = self._find_valid_model_cache(settings.BGE_MODEL_NAME)
                
                if local_model_path:
                    try:
                        logger.info(f"使用本地缓存的sentence-transformers模型: {local_model_path}")
                        self.bge_model = SentenceTransformer(local_model_path, device=self.device)
                        self.model_loaded = True
                        logger.info(f"sentence-transformers模型加载成功 ({'GPU' if self.gpu_available else 'CPU'}模式，本地缓存)")
                        return
                    except Exception as cache_error:
                        logger.warning(f"本地缓存加载失败: {cache_error}")
                
                # 如果本地缓存不存在，尝试从网络下载
                logger.info("从网络下载sentence-transformers模型")
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger.info(f"尝试下载sentence-transformers模型 (第{attempt + 1}次)")
                        self.bge_model = SentenceTransformer(settings.BGE_MODEL_NAME, device=self.device)
                        self.model_loaded = True
                        logger.info(f"sentence-transformers模型加载成功 ({'GPU' if self.gpu_available else 'CPU'}模式)")
                        return
                    except Exception as e:
                        logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(5)  # 等待5秒后重试
                        else:
                            raise e
            except Exception as e2:
                logger.error(f"加载句子变换器模型失败: {e2}")
                # 最后的回退：使用简单的随机向量
                logger.warning("使用随机向量作为回退方案")
                self._use_random_vectors()
                self.model_loaded = True
    
    def _use_random_vectors(self):
        """使用随机向量作为回退方案"""
        import random
        random.seed(42)  # 确保可重现性
        
        def random_encode(texts):
            """生成随机向量"""
            if isinstance(texts, str):
                texts = [texts]
            vectors = []
            for text in texts:
                # 基于文本生成伪随机向量
                random.seed(hash(text) % 2**32)
                vector = [random.uniform(-1, 1) for _ in range(settings.EMBEDDING_DIM)]
                vectors.append(vector)
            return np.array(vectors)
        
        self.bge_model = type('RandomModel', (), {
            'encode': random_encode
        })()
    
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
            if hasattr(self, '_use_random_vectors') and isinstance(self._use_random_vectors, bool) and self._use_random_vectors:
                # 使用随机向量
                result = self.bge_model.encode(full_text)
                if isinstance(result, dict) and 'dense_vecs' in result:
                    return np.array(result['dense_vecs'][0])
                elif isinstance(result, (list, np.ndarray)):
                    return np.array(result[0])
                else:
                    logger.error(f"随机向量编码返回未知类型: {type(result)}")
                    return np.zeros(settings.EMBEDDING_DIM)
            elif BGE_M3_AVAILABLE and hasattr(self.bge_model, 'encode'):
                # 使用BGE-M3模型
                try:
                    logger.debug(f"使用BGE-M3编码文本: {full_text[:100]}...")
                    
                    embeddings = self.bge_model.encode([full_text])
                    logger.debug(f"BGE-M3编码结果类型: {type(embeddings)}")
                    
                    if isinstance(embeddings, dict):
                        if 'dense_vecs' in embeddings and embeddings['dense_vecs'] is not None:
                            dense_vecs = embeddings['dense_vecs']
                            if len(dense_vecs) > 0:
                                result = np.array(dense_vecs[0])
                                logger.debug(f"BGE-M3 dense_vecs编码成功，维度: {result.shape}")
                                return result
                            else:
                                logger.error("BGE-M3 dense_vecs为空")
                                raise ValueError("BGE-M3编码返回空的dense_vecs")
                        else:
                            logger.error("BGE-M3返回的字典中没有有效的dense_vecs")
                            raise ValueError("BGE-M3编码返回无效结果")
                    else:
                        if len(embeddings) > 0:
                            result = np.array(embeddings[0])
                            logger.debug(f"BGE-M3直接编码成功，维度: {result.shape}")
                            return result
                        else:
                            logger.error("BGE-M3编码结果为空")
                            raise ValueError("BGE-M3编码返回空结果")
                except Exception as bge_error:
                    logger.warning(f"BGE-M3编码失败，尝试CPU回退: {bge_error}")
                    # 如果BGE-M3失败，尝试重新加载为CPU模式
                    try:
                        logger.info("重新加载BGE-M3模型为CPU模式")
                        self.device = torch.device('cpu')
                        self.gpu_available = False
                        self.bge_model = BGEM3FlagModel(settings.BGE_MODEL_NAME, use_fp16=False)
                        embeddings = self.bge_model.encode([full_text])
                        if isinstance(embeddings, dict):
                            if 'dense_vecs' in embeddings and embeddings['dense_vecs'] is not None:
                                dense_vecs = embeddings['dense_vecs']
                                if len(dense_vecs) > 0:
                                    result = np.array(dense_vecs[0])
                                    logger.info("BGE-M3 CPU模式编码成功")
                                    return result
                                else:
                                    logger.error("BGE-M3 CPU模式dense_vecs为空")
                                    raise ValueError("BGE-M3 CPU模式编码返回空的dense_vecs")
                            else:
                                logger.error("BGE-M3 CPU模式返回的字典中没有有效的dense_vecs")
                                raise ValueError("BGE-M3 CPU模式编码返回无效结果")
                        else:
                            if len(embeddings) > 0:
                                result = np.array(embeddings[0])
                                logger.info("BGE-M3 CPU模式编码成功")
                                return result
                            else:
                                logger.error("BGE-M3 CPU模式编码结果为空")
                                raise ValueError("BGE-M3 CPU模式编码返回空结果")
                    except Exception as cpu_error:
                        logger.error(f"BGE-M3 CPU模式也失败: {cpu_error}")
                        raise cpu_error
            else:
                # 使用sentence-transformers
                try:
                    logger.debug(f"使用sentence-transformers编码文本: {full_text[:100]}...")
                    embedding = self.bge_model.encode([full_text])
                    result = np.array(embedding[0])
                    logger.debug(f"sentence-transformers编码成功，维度: {result.shape}")
                    return result
                except Exception as st_error:
                    logger.error(f"sentence-transformers编码失败: {st_error}")
                    raise st_error
                
        except Exception as e:
            logger.error(f"编码实体失败: {e}")
            logger.error(f"实体信息: name={entity.name}, type={entity.type}, aliases={entity.aliases}")
            logger.error(f"异常类型: {type(e).__name__}")
            logger.error(f"异常详情: {str(e)}")
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
                # 使用实体名称作为ID，确保能够正确查找
                entity_id = entity.id if entity.id else entity.name
                entity_ids.append(entity_id)
                
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
                    # 尝试通过ID查找实体
                    entity = self._get_db_manager().get_entity(entity_id)
                    if not entity:
                        # 如果通过ID找不到，尝试通过名称搜索
                        entities = self._get_db_manager().search_entities(entity_id, limit=1)
                        entity = entities[0] if entities else None
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