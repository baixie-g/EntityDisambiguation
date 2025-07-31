"""
API请求和响应模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from .entity import Entity, DisambiguationResult, CandidateMatch

class AutoDecideRequest(BaseModel):
    """自动决策请求"""
    entity: Entity = Field(..., description="待消歧的实体")
    force_decision: bool = Field(False, description="是否强制决策，跳过歧义判断")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity": {
                    "name": "糖尿病",
                    "type": "疾病",  # 可选字段
                    "aliases": ["diabetes", "糖尿"],
                    "definition": "糖尿病是一组以高血糖为特征的代谢性疾病...",
                    "attributes": {
                        "症状": ["多尿", "口渴", "体重下降"],
                        "并发症": ["视网膜病变", "肾病"],
                        "治疗方法": ["饮食控制", "胰岛素治疗"]
                    },
                    "source": "临床指南-2022"
                },
                "force_decision": False
            }
        }

class AutoDecideResponse(BaseModel):
    """自动决策响应"""
    result: DisambiguationResult = Field(..., description="消歧结果")
    message: str = Field("", description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "result": {
                    "decision": "merge",
                    "match_id": "disease_00123",
                    "match_entity": {
                        "id": "disease_00123",
                        "name": "糖尿病",
                        "type": "疾病",
                        "aliases": ["diabetes", "糖尿"],
                        "definition": "糖尿病是一组以高血糖为特征的代谢性疾病...",
                        "attributes": {
                            "症状": ["多尿", "口渴", "体重下降"],
                            "并发症": ["视网膜病变", "肾病"],
                            "治疗方法": ["饮食控制", "胰岛素治疗"]
                        },
                        "source": "临床指南-2022",
                        "create_time": "2024-06-10T10:00:00"
                    },
                    "scores": {
                        "bge_score": 0.92,
                        "cross_encoder_score": 0.88,
                        "fuzz_score": 0.95,
                        "levenshtein_score": 0.90,
                        "final_score": 0.91
                    },
                    "confidence": 0.91,
                    "reasoning": "实体名称完全匹配，语义相似度很高，建议合并"
                },
                "message": "自动决策完成"
            }
        }

class MatchCandidatesRequest(BaseModel):
    """匹配候选实体请求"""
    entity: Entity = Field(..., description="待匹配的实体")
    top_k: int = Field(10, description="返回的候选实体数量")
    include_scores: bool = Field(True, description="是否包含详细得分")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity": {
                    "name": "糖尿病",
                    "type": "疾病",  # 可选字段
                    "aliases": ["diabetes"],
                    "definition": "糖尿病是一组以高血糖为特征的代谢性疾病"
                },
                "top_k": 5,
                "include_scores": True
            }
        }

class MatchCandidatesResponse(BaseModel):
    """匹配候选实体响应"""
    candidates: List[CandidateMatch] = Field(..., description="候选实体列表")
    total_count: int = Field(0, description="总候选实体数量")
    message: str = Field("", description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "candidates": [
                    {
                        "entity": {
                            "id": "disease_00123",
                            "name": "糖尿病",
                            "type": "疾病",
                            "aliases": ["diabetes", "糖尿"],
                            "definition": "糖尿病是一组以高血糖为特征的代谢性疾病...",
                            "attributes": {
                                "症状": ["多尿", "口渴", "体重下降"],
                                "并发症": ["视网膜病变", "肾病"],
                                "治疗方法": ["饮食控制", "胰岛素治疗"]
                            },
                            "source": "临床指南-2022",
                            "create_time": "2024-06-10T10:00:00"
                        },
                        "score": {
                            "bge_score": 0.92,
                            "cross_encoder_score": 0.88,
                            "fuzz_score": 0.95,
                            "levenshtein_score": 0.90,
                            "final_score": 0.91
                        },
                        "rank": 1,
                        "similarity_details": "名称完全匹配，语义相似度很高"
                    }
                ],
                "total_count": 1,
                "message": "匹配候选实体完成"
            }
        }

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细错误信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "输入实体格式错误",
                "detail": "实体名称不能为空"
            }
        } 