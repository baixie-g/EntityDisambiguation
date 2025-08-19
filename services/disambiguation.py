"""
实体消歧服务
"""
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import numpy as np
from rapidfuzz import fuzz
from Levenshtein import distance as levenshtein_distance

from models import (
    Entity, 
    CandidateMatch, 
    EntityScore, 
    DisambiguationResult, 
    DecisionType,
    DisambiguationHistory
)
from config.settings import settings

logger = logging.getLogger(__name__)

# 尝试导入CrossEncoder
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers未安装，CrossEncoder功能不可用")

class DisambiguationService:
    """消歧服务类"""
    
    def __init__(self):
        self.cross_encoder: Optional[CrossEncoder] = None
        self.cross_encoder_loaded = False
        
        # 延迟导入数据库管理器和向量化服务以避免循环导入
        self.db_manager = None
        self.vectorization_service = None
    
    def normalize_crossencoder_score(self, score: float) -> float:
        """使用线性归一化CrossEncoder得分"""
        # 基于实际测试结果的得分范围
        min_score = -6.5
        max_score = 7.7
        
        # 线性归一化到[0,1]区间
        normalized = (score - min_score) / (max_score - min_score)
        # 确保在[0,1]范围内
        return max(0.0, min(1.0, float(normalized)))
    
    def _get_db_manager(self):
        """获取数据库管理器实例"""
        if self.db_manager is None:
            from .database_factory import db_manager
            self.db_manager = db_manager
        return self.db_manager
    
    def _get_vectorization_service(self):
        """获取向量化服务实例"""
        if self.vectorization_service is None:
            from .vectorization import vectorization_service
            self.vectorization_service = vectorization_service
        return self.vectorization_service

    def load_cross_encoder(self):
        """加载CrossEncoder模型"""
        if self.cross_encoder_loaded:
            return
            
        try:
            logger.info(f"加载CrossEncoder模型: {settings.CROSS_ENCODER_MODEL_NAME}")
            
            # 优先使用本地缓存
            from pathlib import Path
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            model_dir = cache_dir / "models--cross-encoder--ms-marco-MiniLM-L-6-v2"
            
            if model_dir.exists():
                # 查找snapshots下的最新快照
                snapshots_dir = model_dir / "snapshots"
                if snapshots_dir.exists():
                    snapshots = list(snapshots_dir.iterdir())
                    if snapshots:
                        # 按修改时间排序，取最新的
                        latest_snapshot = max(snapshots, key=lambda x: x.stat().st_mtime)
                        model_path = str(latest_snapshot)
                        logger.info(f"发现本地CrossEncoder模型缓存: {model_path}")
                        try:
                            self.cross_encoder = CrossEncoder(model_path)
                            self.cross_encoder_loaded = True
                            logger.info("CrossEncoder模型加载成功 (本地缓存)")
                            return
                        except Exception as cache_error:
                            logger.warning(f"本地缓存加载失败: {cache_error}")
            
            # 如果本地缓存不存在或加载失败，尝试从网络下载
            logger.info("本地缓存不可用，尝试从网络下载CrossEncoder模型")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"尝试下载CrossEncoder模型 (第{attempt + 1}次)")
                    self.cross_encoder = CrossEncoder(settings.CROSS_ENCODER_MODEL_NAME)
                    self.cross_encoder_loaded = True
                    logger.info("CrossEncoder模型加载成功")
                    return
                except Exception as e:
                    logger.warning(f"第{attempt + 1}次尝试失败: {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(5)  # 等待5秒后重试
                    else:
                        raise e
                        
        except Exception as e:
            logger.error(f"加载CrossEncoder模型失败: {e}")
            self.cross_encoder = None
    
    def auto_decide(self, input_entity: Entity, force_decision: bool = False, db_key: Optional[str] = None) -> DisambiguationResult:
        """自动决策实体消歧"""
        try:
            # 步骤1: 智能搜索相似实体
            similar_entities = self._smart_search_similar_entities(input_entity, top_k=settings.FAISS_TOP_K, db_key=db_key)
            
            if not similar_entities:
                # 没有找到相似实体，直接新建
                result = DisambiguationResult(
                    decision=DecisionType.CREATE,
                    scores=EntityScore(),
                    confidence=1.0,
                    reasoning="没有找到相似实体，建议新建"
                )
                self._save_history(input_entity, result)
                return result
            
            # 步骤2: 计算各种相似度得分
            candidates = []
            
            for candidate_entity, bge_score in similar_entities:
                # 计算综合得分
                score = self._calculate_comprehensive_score(input_entity, candidate_entity, bge_score)
                candidates.append((candidate_entity, score))
            
            # 按得分排序
            candidates.sort(key=lambda x: x[1].final_score, reverse=True)
            
            # 步骤3: 根据最高得分做决策
            best_candidate, best_score = candidates[0]
            
            result = self._make_decision(input_entity, best_candidate, best_score, force_decision)
            
            # 保存历史记录
            self._save_history(input_entity, result)
            
            return result
            
        except Exception as e:
            logger.error(f"自动决策失败: {e}")
            # 返回错误结果
            return DisambiguationResult(
                decision=DecisionType.CREATE,
                scores=EntityScore(),
                confidence=0.0,
                reasoning=f"处理失败: {str(e)}"
            )
    
    def _smart_search_similar_entities(self, input_entity: Entity, top_k: int = 10, db_key: Optional[str] = None) -> List[Tuple[Entity, float]]:
        """智能搜索相似实体，支持可选的type字段"""
        try:
            # 首先尝试使用FAISS向量搜索
            vector_similar_entities = self._get_vectorization_service().search_similar_entities(input_entity, top_k=top_k*2, db_key=db_key)
            
            # 如果提供了type字段，优先在指定type中搜索
            if input_entity.type:
                logger.info(f"在指定类型 '{input_entity.type}' 中搜索相似实体")
                
                # 获取指定type的所有实体
                type_entities = self._get_db_manager().get_entities_by_type(input_entity.type, db_key=db_key)
                
                if type_entities:
                    # 在指定type中计算相似度
                    type_similar_entities = []
                    for entity in type_entities:
                        # 使用向量化服务计算相似度
                        vector_score = self._get_vectorization_service().get_entity_vector(entity)
                        if vector_score is not None:
                            input_vector = self._get_vectorization_service().get_entity_vector(input_entity)
                            if input_vector is not None:
                                # 计算余弦相似度
                                similarity = np.dot(input_vector, vector_score) / (np.linalg.norm(input_vector) * np.linalg.norm(vector_score))
                                # 降低阈值，确保能找到更多候选
                                if similarity > 0.1:  # 使用更低的阈值
                                    type_similar_entities.append((entity, float(similarity)))
                    
                    # 按相似度排序
                    type_similar_entities.sort(key=lambda x: x[1], reverse=True)
                    
                    # 合并向量搜索结果和类型搜索结果
                    all_similar_entities = []
                    seen_entities = set()
                    
                    # 优先添加类型搜索结果
                    for entity, score in type_similar_entities:
                        if entity.name not in seen_entities:
                            all_similar_entities.append((entity, score))
                            seen_entities.add(entity.name)
                    
                    # 添加向量搜索结果
                    for entity, score in vector_similar_entities:
                        if entity.name not in seen_entities:
                            all_similar_entities.append((entity, score))
                            seen_entities.add(entity.name)
                    
                    return all_similar_entities[:top_k]
            
            # 如果没有type或type中没有找到相似实体，返回向量搜索结果
            logger.info("在所有实体中搜索相似实体")
            return vector_similar_entities[:top_k]
            
        except Exception as e:
            logger.error(f"智能搜索相似实体失败: {e}")
            # 降级到全局搜索
            return self._get_vectorization_service().search_similar_entities(input_entity, top_k, db_key=db_key)
    
    def match_candidates(self, input_entity: Entity, top_k: int = 10, db_key: Optional[str] = None) -> List[CandidateMatch]:
        """获取匹配候选实体"""
        try:
            # 使用智能搜索逻辑
            similar_entities = self._smart_search_similar_entities(input_entity, top_k=top_k, db_key=db_key)
            
            if not similar_entities:
                return []
            
            # 计算详细得分
            candidates = []
            
            for rank, (candidate_entity, bge_score) in enumerate(similar_entities, 1):
                # 计算综合得分
                score = self._calculate_comprehensive_score(input_entity, candidate_entity, bge_score)
                
                # 生成相似度详情
                similarity_details = self._generate_similarity_details(input_entity, candidate_entity, score)
                
                candidate = CandidateMatch(
                    entity=candidate_entity,
                    score=score,
                    rank=rank,
                    similarity_details=similarity_details
                )
                candidates.append(candidate)
            
            return candidates
            
        except Exception as e:
            logger.error(f"匹配候选实体失败: {e}")
            return []
    
    def _calculate_comprehensive_score(self, input_entity: Entity, candidate_entity: Entity, bge_score: float) -> EntityScore:
        """计算综合相似度得分"""
        score = EntityScore(bge_score=bge_score)
        
        try:
            # 步骤1: CrossEncoder重排序得分
            if not self.cross_encoder_loaded:
                self.load_cross_encoder()
            
            if self.cross_encoder:
                input_text = self._entity_to_text(input_entity)
                candidate_text = self._entity_to_text(candidate_entity)
                
                cross_score = self.cross_encoder.predict([(input_text, candidate_text)])[0]
                # 使用sigmoid归一化CrossEncoder得分
                score.cross_encoder_score = self.normalize_crossencoder_score(float(cross_score))
            
            # 步骤2: RapidFuzz字符串相似度
            score.fuzz_score = self._calculate_fuzz_score(input_entity, candidate_entity)
            
            # 步骤3: Levenshtein编辑距离
            score.levenshtein_score = self._calculate_levenshtein_score(input_entity, candidate_entity)
            
            # 步骤4: 计算加权最终得分
            score.final_score = (
                score.bge_score * settings.BGE_WEIGHT +
                score.cross_encoder_score * settings.CROSS_ENCODER_WEIGHT +
                score.fuzz_score * settings.FUZZ_WEIGHT +
                score.levenshtein_score * settings.LEVENSHTEIN_WEIGHT
            )
            
            # 步骤5: 应用类型匹配权重
            type_multiplier = self._calculate_type_multiplier(input_entity, candidate_entity)
            score.final_score *= type_multiplier
            
        except Exception as e:
            logger.error(f"计算综合得分失败: {e}")
            score.final_score = bge_score * 0.5  # 降级处理
        
        return score
    
    def _calculate_type_multiplier(self, input_entity: Entity, candidate_entity: Entity) -> float:
        """计算类型匹配权重倍数"""
        # 如果任一实体没有类型信息，返回中性权重
        if not input_entity.type or not candidate_entity.type:
            return 1.0
        
        # 类型完全匹配
        if input_entity.type == candidate_entity.type:
            return settings.TYPE_MATCH_BONUS
        
        # 类型不匹配，应用惩罚
        return settings.TYPE_MISMATCH_PENALTY
    
    def _calculate_fuzz_score(self, input_entity: Entity, candidate_entity: Entity) -> float:
        """计算RapidFuzz相似度得分"""
        try:
            # 名称相似度
            name_score = fuzz.token_sort_ratio(input_entity.name, candidate_entity.name) / 100.0
            
            # 别名相似度
            alias_scores = []
            for input_alias in input_entity.aliases:
                for candidate_alias in candidate_entity.aliases:
                    alias_scores.append(fuzz.token_sort_ratio(input_alias, candidate_alias) / 100.0)
            
            # 与候选实体名称的别名相似度
            for input_alias in input_entity.aliases:
                alias_scores.append(fuzz.token_sort_ratio(input_alias, candidate_entity.name) / 100.0)
            
            # 与输入实体名称的别名相似度
            for candidate_alias in candidate_entity.aliases:
                alias_scores.append(fuzz.token_sort_ratio(input_entity.name, candidate_alias) / 100.0)
            
            # 取最高得分
            max_alias_score = max(alias_scores) if alias_scores else 0.0
            
            # 返回名称和别名得分的最大值
            return max(name_score, max_alias_score)
            
        except Exception as e:
            logger.error(f"计算RapidFuzz得分失败: {e}")
            return 0.0
    
    def _calculate_levenshtein_score(self, input_entity: Entity, candidate_entity: Entity) -> float:
        """计算Levenshtein编辑距离得分"""
        try:
            # 名称编辑距离
            name_distance = levenshtein_distance(input_entity.name, candidate_entity.name)
            max_name_len = max(len(input_entity.name), len(candidate_entity.name))
            name_score = 1.0 - (name_distance / max_name_len) if max_name_len > 0 else 0.0
            
            # 别名编辑距离
            alias_scores = []
            for input_alias in input_entity.aliases:
                for candidate_alias in candidate_entity.aliases:
                    distance = levenshtein_distance(input_alias, candidate_alias)
                    max_len = max(len(input_alias), len(candidate_alias))
                    alias_scores.append(1.0 - (distance / max_len) if max_len > 0 else 0.0)
            
            # 与候选实体名称的别名编辑距离
            for input_alias in input_entity.aliases:
                distance = levenshtein_distance(input_alias, candidate_entity.name)
                max_len = max(len(input_alias), len(candidate_entity.name))
                alias_scores.append(1.0 - (distance / max_len) if max_len > 0 else 0.0)
            
            # 与输入实体名称的别名编辑距离
            for candidate_alias in candidate_entity.aliases:
                distance = levenshtein_distance(input_entity.name, candidate_alias)
                max_len = max(len(input_entity.name), len(candidate_alias))
                alias_scores.append(1.0 - (distance / max_len) if max_len > 0 else 0.0)
            
            # 取最高得分
            max_alias_score = max(alias_scores) if alias_scores else 0.0
            
            # 返回名称和别名得分的最大值
            return max(name_score, max_alias_score)
            
        except Exception as e:
            logger.error(f"计算Levenshtein得分失败: {e}")
            return 0.0
    
    def _make_decision(self, input_entity: Entity, candidate_entity: Entity, score: EntityScore, force_decision: bool) -> DisambiguationResult:
        """根据得分做消歧决策"""
        try:
            final_score = score.final_score
            
            if final_score >= settings.HIGH_THRESHOLD:
                # 高于高阈值，合并
                decision = DecisionType.MERGE
                reasoning = f"相似度得分{final_score:.3f}高于阈值{settings.HIGH_THRESHOLD}，建议合并"
            elif final_score <= settings.LOW_THRESHOLD:
                # 低于低阈值，新建
                decision = DecisionType.CREATE
                reasoning = f"相似度得分{final_score:.3f}低于阈值{settings.LOW_THRESHOLD}，建议新建"
            else:
                # 在中间区间
                if force_decision:
                    # 强制决策，选择得分更高的操作
                    if final_score > (settings.HIGH_THRESHOLD + settings.LOW_THRESHOLD) / 2:
                        decision = DecisionType.MERGE
                        reasoning = f"强制决策：相似度得分{final_score:.3f}，选择合并"
                    else:
                        decision = DecisionType.CREATE
                        reasoning = f"强制决策：相似度得分{final_score:.3f}，选择新建"
                else:
                    # 标记为歧义，需要人工审核
                    decision = DecisionType.AMBIGUOUS
                    reasoning = f"相似度得分{final_score:.3f}处于歧义区间[{settings.LOW_THRESHOLD}, {settings.HIGH_THRESHOLD}]，需要人工审核"
            
            return DisambiguationResult(
                decision=decision,
                match_id=candidate_entity.id if decision == DecisionType.MERGE else None,
                match_entity=candidate_entity if decision == DecisionType.MERGE else None,
                scores=score,
                confidence=final_score,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"做消歧决策失败: {e}")
            return DisambiguationResult(
                decision=DecisionType.CREATE,
                scores=score,
                confidence=0.0,
                reasoning=f"决策失败: {str(e)}"
            )
    
    def _entity_to_text(self, entity: Entity) -> str:
        """将实体转换为文本"""
        parts = [entity.name]
        
        if entity.aliases:
            parts.extend(entity.aliases)
        
        if entity.definition:
            parts.append(entity.definition)
        
        return " ".join(parts)
    
    def _generate_similarity_details(self, input_entity: Entity, candidate_entity: Entity, score: EntityScore) -> str:
        """生成相似度详情说明"""
        details = []
        
        # 基本信息
        details.append(f"输入实体: {input_entity.name} ({input_entity.type or '无类型'})")
        details.append(f"候选实体: {candidate_entity.name} ({candidate_entity.type or '无类型'})")
        
        # 类型匹配信息
        if input_entity.type and candidate_entity.type:
            if input_entity.type == candidate_entity.type:
                details.append(f"✅ 类型匹配: {input_entity.type}")
            else:
                details.append(f"❌ 类型不匹配: {input_entity.type} vs {candidate_entity.type}")
        else:
            details.append("⚠️ 类型信息不完整")
        
        # 各项得分
        details.append(f"BGE向量相似度: {score.bge_score:.3f}")
        details.append(f"CrossEncoder重排序: {score.cross_encoder_score:.3f}")
        details.append(f"字符串模糊匹配: {score.fuzz_score:.3f}")
        details.append(f"编辑距离相似度: {score.levenshtein_score:.3f}")
        details.append(f"最终加权得分: {score.final_score:.3f}")
        
        return "\n".join(details)
    
    def _save_history(self, input_entity: Entity, result: DisambiguationResult):
        """保存消歧历史"""
        try:
            history = DisambiguationHistory(
                input_entity=input_entity,
                decision=result.decision,
                match_id=result.match_id,
                match_entity=result.match_entity,
                scores=result.scores,
                reasoning=result.reasoning,
                timestamp=datetime.now()
            )
            
            self._get_db_manager().save_disambiguation_history(history)
            
        except Exception as e:
            logger.error(f"保存消歧历史失败: {e}")
    
    def get_disambiguation_history(self, limit: int = 100) -> List[DisambiguationHistory]:
        """获取消歧历史"""
        return self._get_db_manager().get_disambiguation_history(limit)
    
    def get_disambiguation_stats(self) -> Dict[str, Any]:
        """获取消歧统计信息"""
        try:
            histories = self.get_disambiguation_history(1000)  # 最近1000条记录
            
            total_count = len(histories)
            merge_count = sum(1 for h in histories if h.decision == DecisionType.MERGE)
            create_count = sum(1 for h in histories if h.decision == DecisionType.CREATE)
            ambiguous_count = sum(1 for h in histories if h.decision == DecisionType.AMBIGUOUS)
            
            return {
                "total_count": total_count,
                "merge_count": merge_count,
                "create_count": create_count,
                "ambiguous_count": ambiguous_count,
                "merge_rate": merge_count / total_count if total_count > 0 else 0,
                "create_rate": create_count / total_count if total_count > 0 else 0,
                "ambiguous_rate": ambiguous_count / total_count if total_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取消歧统计失败: {e}")
            return {}

# 全局消歧服务实例
disambiguation_service = DisambiguationService() 