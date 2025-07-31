#!/usr/bin/env python3
"""
测试各个模型的得分范围
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings

def test_score_ranges():
    """测试各个模型的得分范围"""
    
    print("=" * 80)
    print("各模型得分范围分析")
    print("=" * 80)
    
    # 测试不同得分组合
    test_cases = [
        {
            "name": "完美匹配",
            "scores": {"bge": 1.0, "cross": 1.0, "fuzz": 1.0, "levenshtein": 1.0}
        },
        {
            "name": "高匹配",
            "scores": {"bge": 0.9, "cross": 0.8, "fuzz": 0.9, "levenshtein": 0.8}
        },
        {
            "name": "中等匹配",
            "scores": {"bge": 0.7, "cross": 0.6, "fuzz": 0.5, "levenshtein": 0.4}
        },
        {
            "name": "低匹配",
            "scores": {"bge": 0.3, "cross": 0.2, "fuzz": 0.1, "levenshtein": 0.0}
        },
        {
            "name": "极低匹配",
            "scores": {"bge": 0.1, "cross": 0.0, "fuzz": 0.0, "levenshtein": 0.0}
        }
    ]
    
    print("\n📊 各模型得分范围:")
    print(f"  BGE-M3向量相似度: 0.0 - 1.0 (权重: {settings.BGE_WEIGHT})")
    print(f"  CrossEncoder重排序: 0.0 - 1.0 (权重: {settings.CROSS_ENCODER_WEIGHT})")
    print(f"  RapidFuzz字符串匹配: 0.0 - 1.0 (权重: {settings.FUZZ_WEIGHT})")
    print(f"  Levenshtein编辑距离: 0.0 - 1.0 (权重: {settings.LEVENSHTEIN_WEIGHT})")
    
    print("\n🧮 加权得分计算:")
    print("  加权得分 = BGE×0.4 + CrossEncoder×0.3 + Fuzz×0.2 + Levenshtein×0.1")
    print("  理论范围: 0.0 - 1.0")
    
    print("\n🎯 类型匹配影响:")
    print(f"  类型匹配倍数: {settings.TYPE_MATCH_BONUS}")
    print(f"  类型不匹配倍数: {settings.TYPE_MISMATCH_PENALTY}")
    print("  类型信息缺失倍数: 1.0")
    
    print("\n" + "=" * 80)
    print("详细测试结果")
    print("=" * 80)
    
    for case in test_cases:
        print(f"\n📋 {case['name']}:")
        print("-" * 50)
        
        scores = case['scores']
        
        # 计算加权得分
        weighted_score = (
            scores['bge'] * settings.BGE_WEIGHT +
            scores['cross'] * settings.CROSS_ENCODER_WEIGHT +
            scores['fuzz'] * settings.FUZZ_WEIGHT +
            scores['levenshtein'] * settings.LEVENSHTEIN_WEIGHT
        )
        
        print(f"  BGE得分: {scores['bge']:.3f} × {settings.BGE_WEIGHT:.1f} = {scores['bge'] * settings.BGE_WEIGHT:.3f}")
        print(f"  CrossEncoder得分: {scores['cross']:.3f} × {settings.CROSS_ENCODER_WEIGHT:.1f} = {scores['cross'] * settings.CROSS_ENCODER_WEIGHT:.3f}")
        print(f"  Fuzz得分: {scores['fuzz']:.3f} × {settings.FUZZ_WEIGHT:.1f} = {scores['fuzz'] * settings.FUZZ_WEIGHT:.3f}")
        print(f"  Levenshtein得分: {scores['levenshtein']:.3f} × {settings.LEVENSHTEIN_WEIGHT:.1f} = {scores['levenshtein'] * settings.LEVENSHTEIN_WEIGHT:.3f}")
        print(f"  加权得分: {weighted_score:.3f}")
        
        # 计算最终得分
        type_match_score = weighted_score * settings.TYPE_MATCH_BONUS
        type_mismatch_score = weighted_score * settings.TYPE_MISMATCH_PENALTY
        type_neutral_score = weighted_score * 1.0
        
        print(f"  类型匹配最终得分: {type_match_score:.3f}")
        print(f"  类型不匹配最终得分: {type_mismatch_score:.3f}")
        print(f"  类型缺失最终得分: {type_neutral_score:.3f}")
        
        # 决策分析
        print(f"  决策分析:")
        if type_match_score >= settings.HIGH_THRESHOLD:
            print(f"    ✅ 类型匹配: 直接合并 (得分 {type_match_score:.3f} ≥ {settings.HIGH_THRESHOLD})")
        elif type_match_score <= settings.LOW_THRESHOLD:
            print(f"    ❌ 类型匹配: 直接新建 (得分 {type_match_score:.3f} ≤ {settings.LOW_THRESHOLD})")
        else:
            print(f"    ⚠️ 类型匹配: 需要人工判断 (得分 {type_match_score:.3f})")
            
        if type_mismatch_score >= settings.HIGH_THRESHOLD:
            print(f"    ✅ 类型不匹配: 直接合并 (得分 {type_mismatch_score:.3f} ≥ {settings.HIGH_THRESHOLD})")
        elif type_mismatch_score <= settings.LOW_THRESHOLD:
            print(f"    ❌ 类型不匹配: 直接新建 (得分 {type_mismatch_score:.3f} ≤ {settings.LOW_THRESHOLD})")
        else:
            print(f"    ⚠️ 类型不匹配: 需要人工判断 (得分 {type_mismatch_score:.3f})")
    
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    
    print("📈 得分范围总结:")
    print("  1. 各模型得分范围: 0.0 - 1.0")
    print("  2. 加权得分范围: 0.0 - 1.0")
    print("  3. 最终得分范围:")
    print(f"     - 类型匹配: 0.0 - {settings.TYPE_MATCH_BONUS:.1f}")
    print(f"     - 类型不匹配: 0.0 - {settings.TYPE_MISMATCH_PENALTY:.1f}")
    print("     - 类型缺失: 0.0 - 1.0")
    
    print("\n⚠️ 当前配置问题:")
    print(f"  - 类型不匹配惩罚过重: {settings.TYPE_MISMATCH_PENALTY}倍")
    print(f"  - 高阈值过高: {settings.HIGH_THRESHOLD}")
    print(f"  - 低阈值过高: {settings.LOW_THRESHOLD}")
    
    print("\n🔧 建议调整:")
    print("  TYPE_MISMATCH_PENALTY: 0.1 → 0.3")
    print("  TYPE_MATCH_BONUS: 1.0 → 1.1")
    print("  HIGH_THRESHOLD: 1.0 → 0.85")
    print("  LOW_THRESHOLD: 0.5 → 0.3")

if __name__ == "__main__":
    test_score_ranges() 