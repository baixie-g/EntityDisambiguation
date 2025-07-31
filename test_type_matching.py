#!/usr/bin/env python3
"""
测试实体类型匹配对消歧评分的影响
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.entity import Entity
from services.disambiguation import DisambiguationService
from config.settings import settings

def test_type_matching():
    """测试类型匹配对评分的影响"""
    
    # 初始化消歧服务
    disambiguation_service = DisambiguationService()
    
    # 测试用例1: 类型不匹配的情况
    print("=" * 60)
    print("测试用例1: 类型不匹配")
    print("=" * 60)
    
    input_entity = Entity(
        name="机械与动力工程",
        type="技术",
        aliases=[],
        definition="-",
        attributes={}
    )
    
    candidate_entity = Entity(
        id="person_003_1753926297509",
        name="小李",
        type="人物",
        aliases=[],
        definition="专注新能源材料研究，毕业于上海交通大学机械与动力工程学院，现任职宁德时代新能源科技股份有限公司首席材料科学家",
        attributes={
            "毕业院校": ["上海交通大学"],
            "工作单位": ["宁德时代新能源科技股份有限公司"],
            "职位": ["首席材料科学家"],
            "研究领域": ["新能源材料研究"]
        }
    )
    
    # 模拟BGE得分
    bge_score = 0.75  # 假设的向量相似度得分
    
    # 计算综合得分
    score = disambiguation_service._calculate_comprehensive_score(input_entity, candidate_entity, bge_score)
    
    print(f"输入实体: {input_entity.name} ({input_entity.type})")
    print(f"候选实体: {candidate_entity.name} ({candidate_entity.type})")
    print(f"类型匹配倍数: {disambiguation_service._calculate_type_multiplier(input_entity, candidate_entity)}")
    print(f"BGE得分: {score.bge_score:.3f}")
    print(f"CrossEncoder得分: {score.cross_encoder_score:.3f}")
    print(f"Fuzz得分: {score.fuzz_score:.3f}")
    print(f"Levenshtein得分: {score.levenshtein_score:.3f}")
    print(f"最终得分: {score.final_score:.3f}")
    
    # 测试用例2: 类型匹配的情况
    print("\n" + "=" * 60)
    print("测试用例2: 类型匹配")
    print("=" * 60)
    
    input_entity2 = Entity(
        name="机械与动力工程",
        type="技术",
        aliases=[],
        definition="-",
        attributes={}
    )
    
    candidate_entity2 = Entity(
        id="tech_001",
        name="机械工程",
        type="技术",
        aliases=["机械工程学"],
        definition="机械工程是一门涉及机械设计、制造、维护和应用的工程学科",
        attributes={
            "学科分类": ["工程学"],
            "相关领域": ["动力工程", "材料科学"]
        }
    )
    
    # 计算综合得分
    score2 = disambiguation_service._calculate_comprehensive_score(input_entity2, candidate_entity2, bge_score)
    
    print(f"输入实体: {input_entity2.name} ({input_entity2.type})")
    print(f"候选实体: {candidate_entity2.name} ({candidate_entity2.type})")
    print(f"类型匹配倍数: {disambiguation_service._calculate_type_multiplier(input_entity2, candidate_entity2)}")
    print(f"BGE得分: {score2.bge_score:.3f}")
    print(f"CrossEncoder得分: {score2.cross_encoder_score:.3f}")
    print(f"Fuzz得分: {score2.fuzz_score:.3f}")
    print(f"Levenshtein得分: {score2.levenshtein_score:.3f}")
    print(f"最终得分: {score2.final_score:.3f}")
    
    # 对比分析
    print("\n" + "=" * 60)
    print("对比分析")
    print("=" * 60)
    
    print(f"类型不匹配最终得分: {score.final_score:.3f}")
    print(f"类型匹配最终得分: {score2.final_score:.3f}")
    print(f"得分差异: {score2.final_score - score.final_score:.3f}")
    print(f"类型匹配提升倍数: {score2.final_score / score.final_score:.2f}x")
    
    # 配置信息
    print("\n" + "=" * 60)
    print("当前配置")
    print("=" * 60)
    print(f"类型不匹配惩罚权重: {settings.TYPE_MISMATCH_PENALTY}")
    print(f"类型匹配奖励权重: {settings.TYPE_MATCH_BONUS}")
    print(f"BGE权重: {settings.BGE_WEIGHT}")
    print(f"CrossEncoder权重: {settings.CROSS_ENCODER_WEIGHT}")
    print(f"Fuzz权重: {settings.FUZZ_WEIGHT}")
    print(f"Levenshtein权重: {settings.LEVENSHTEIN_WEIGHT}")

if __name__ == "__main__":
    test_type_matching() 