"""
实体数据模型
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class EntityType(str, Enum):
    """实体类型枚举"""
    DISEASE = "疾病"
    SYMPTOM = "症状"
    DRUG = "药物"
    TREATMENT = "治疗"
    GENE = "基因"
    PROTEIN = "蛋白质"
    ORGAN = "器官"
    OTHER = "其他"

class Entity(BaseModel):
    """实体模型"""
    id: Optional[str] = None
    name: str = Field(..., description="实体名称")
    type: EntityType = Field(..., description="实体类型")
    aliases: List[str] = Field(default_factory=list, description="别名列表")
    definition: Optional[str] = Field(None, description="实体定义")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="实体属性")
    source: Optional[str] = Field(None, description="数据来源")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class EntityScore(BaseModel):
    """实体相似度得分"""
    bge_score: float = Field(0.0, description="BGE-M3向量相似度得分")
    cross_encoder_score: float = Field(0.0, description="CrossEncoder重排序得分")
    fuzz_score: float = Field(0.0, description="RapidFuzz字符串匹配得分")
    levenshtein_score: float = Field(0.0, description="Levenshtein编辑距离得分")
    final_score: float = Field(0.0, description="最终加权得分")

class DecisionType(str, Enum):
    """决策类型枚举"""
    MERGE = "merge"
    CREATE = "create"
    AMBIGUOUS = "ambiguous"

class DisambiguationResult(BaseModel):
    """消歧结果"""
    decision: DecisionType = Field(..., description="决策类型")
    match_id: Optional[str] = Field(None, description="匹配的实体ID")
    match_entity: Optional[Entity] = Field(None, description="匹配的实体")
    scores: EntityScore = Field(..., description="相似度得分")
    confidence: float = Field(0.0, description="置信度")
    reasoning: str = Field("", description="决策推理过程")

class DisambiguationHistory(BaseModel):
    """消歧历史记录"""
    id: Optional[int] = None
    input_entity: Entity = Field(..., description="输入实体")
    decision: DecisionType = Field(..., description="决策类型")
    match_id: Optional[str] = Field(None, description="匹配的实体ID")
    match_entity: Optional[Entity] = Field(None, description="匹配的实体")
    scores: EntityScore = Field(..., description="相似度得分")
    reasoning: str = Field("", description="决策推理过程")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class CandidateMatch(BaseModel):
    """候选匹配实体"""
    entity: Entity = Field(..., description="候选实体")
    score: EntityScore = Field(..., description="匹配得分")
    rank: int = Field(..., description="排名")
    similarity_details: str = Field("", description="相似度详情") 