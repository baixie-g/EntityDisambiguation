#!/usr/bin/env python3
"""
简化的类型匹配测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.entity import Entity
from config.settings import settings

def calculate_type_multiplier(input_entity: Entity, candidate_entity: Entity) -> float:
    """计算类型匹配权重倍数"""
    # 如果任一实体没有类型信息，返回中性权重
    if not input_entity.type or not candidate_entity.type:
        return 1.0
    
    # 类型完全匹配
    if input_entity.type == candidate_entity.type:
        return settings.TYPE_MATCH_BONUS
    
    # 类型不匹配，应用惩罚
    return settings.TYPE_MISMATCH_PENALTY

def simulate_score_calculation(input_entity: Entity, candidate_entity: Entity, bge_score: float = 0.75) -> dict:
    """模拟评分计算"""
    # 模拟各项得分
    cross_encoder_score = 0.8  # 模拟CrossEncoder得分
    fuzz_score = 0.3  # 模拟字符串匹配得分
    levenshtein_score = 0.4  # 模拟编辑距离得分
    
    # 计算加权得分
    weighted_score = (
        bge_score * settings.BGE_WEIGHT +
        cross_encoder_score * settings.CROSS_ENCODER_WEIGHT +
        fuzz_score * settings.FUZZ_WEIGHT +
        levenshtein_score * settings.LEVENSHTEIN_WEIGHT
    )
    
    # 应用类型匹配权重
    type_multiplier = calculate_type_multiplier(input_entity, candidate_entity)
    final_score = weighted_score * type_multiplier
    
    return {
        'bge_score': bge_score,
        'cross_encoder_score': cross_encoder_score,
        'fuzz_score': fuzz_score,
        'levenshtein_score': levenshtein_score,
        'weighted_score': weighted_score,
        'type_multiplier': type_multiplier,
        'final_score': final_score
    }

def test_type_matching():
    """测试类型匹配对评分的影响"""
    
    print("=" * 80)
    print("实体类型匹配对消歧评分的影响测试")
    print("=" * 80)
    
    # 测试用例1: 类型不匹配的情况
    print("\n📋 测试用例1: 类型不匹配")
    print("-" * 50)
    
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
    
    score1 = simulate_score_calculation(input_entity, candidate_entity)
    
    print(f"输入实体: {input_entity.name} ({input_entity.type})")
    print(f"候选实体: {candidate_entity.name} ({candidate_entity.type})")
    print(f"类型匹配倍数: {score1['type_multiplier']}")
    print(f"BGE得分: {score1['bge_score']:.3f}")
    print(f"CrossEncoder得分: {score1['cross_encoder_score']:.3f}")
    print(f"Fuzz得分: {score1['fuzz_score']:.3f}")
    print(f"Levenshtein得分: {score1['levenshtein_score']:.3f}")
    print(f"加权得分: {score1['weighted_score']:.3f}")
    print(f"最终得分: {score1['final_score']:.3f}")
    
    # 测试用例2: 类型匹配的情况
    print("\n📋 测试用例2: 类型匹配")
    print("-" * 50)
    
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
    
    score2 = simulate_score_calculation(input_entity2, candidate_entity2)
    
    print(f"输入实体: {input_entity2.name} ({input_entity2.type})")
    print(f"候选实体: {candidate_entity2.name} ({candidate_entity2.type})")
    print(f"类型匹配倍数: {score2['type_multiplier']}")
    print(f"BGE得分: {score2['bge_score']:.3f}")
    print(f"CrossEncoder得分: {score2['cross_encoder_score']:.3f}")
    print(f"Fuzz得分: {score2['fuzz_score']:.3f}")
    print(f"Levenshtein得分: {score2['levenshtein_score']:.3f}")
    print(f"加权得分: {score2['weighted_score']:.3f}")
    print(f"最终得分: {score2['final_score']:.3f}")
    
    # 对比分析
    print("\n📊 对比分析")
    print("-" * 50)
    
    print(f"类型不匹配最终得分: {score1['final_score']:.3f}")
    print(f"类型匹配最终得分: {score2['final_score']:.3f}")
    print(f"得分差异: {score2['final_score'] - score1['final_score']:.3f}")
    print(f"类型匹配提升倍数: {score2['final_score'] / score1['final_score']:.2f}x")
    
    # 配置信息
    print("\n⚙️ 当前配置")
    print("-" * 50)
    print(f"类型不匹配惩罚权重: {settings.TYPE_MISMATCH_PENALTY}")
    print(f"类型匹配奖励权重: {settings.TYPE_MATCH_BONUS}")
    print(f"BGE权重: {settings.BGE_WEIGHT}")
    print(f"CrossEncoder权重: {settings.CROSS_ENCODER_WEIGHT}")
    print(f"Fuzz权重: {settings.FUZZ_WEIGHT}")
    print(f"Levenshtein权重: {settings.LEVENSHTEIN_WEIGHT}")
    
    # 评分范围说明
    print("\n📈 评分范围说明")
    print("-" * 50)
    print("• 总分: 理论上没有明确上限，但通常在0.0-1.5之间")
    print("• 各组件得分范围: 0.0-1.0")
    print("• 类型匹配影响:")
    print(f"  - 类型不匹配时: 最终得分 × {settings.TYPE_MISMATCH_PENALTY}")
    print(f"  - 类型匹配时: 最终得分 × {settings.TYPE_MATCH_BONUS}")
    print("• 决策阈值:")
    print(f"  - 高阈值 (直接合并): {settings.HIGH_THRESHOLD}")
    print(f"  - 低阈值 (直接新建): {settings.LOW_THRESHOLD}")

if __name__ == "__main__":
    test_type_matching() 