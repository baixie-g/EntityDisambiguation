#!/usr/bin/env python3
"""
验证权重计算公式的正确性
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings

def verify_formula():
    """验证权重计算公式"""
    
    print("=" * 60)
    print("权重计算公式验证")
    print("=" * 60)
    
    # 模拟各项得分
    bge_score = 0.8
    cross_encoder_score = 0.7
    fuzz_score = 0.6
    levenshtein_score = 0.5
    
    # 计算加权得分
    weighted_score = (
        bge_score * settings.BGE_WEIGHT +
        cross_encoder_score * settings.CROSS_ENCODER_WEIGHT +
        fuzz_score * settings.FUZZ_WEIGHT +
        levenshtein_score * settings.LEVENSHTEIN_WEIGHT
    )
    
    print("📊 各项得分:")
    print(f"  BGE得分: {bge_score:.3f} × {settings.BGE_WEIGHT:.1f} = {bge_score * settings.BGE_WEIGHT:.3f}")
    print(f"  CrossEncoder得分: {cross_encoder_score:.3f} × {settings.CROSS_ENCODER_WEIGHT:.1f} = {cross_encoder_score * settings.CROSS_ENCODER_WEIGHT:.3f}")
    print(f"  Fuzz得分: {fuzz_score:.3f} × {settings.FUZZ_WEIGHT:.1f} = {fuzz_score * settings.FUZZ_WEIGHT:.3f}")
    print(f"  Levenshtein得分: {levenshtein_score:.3f} × {settings.LEVENSHTEIN_WEIGHT:.1f} = {levenshtein_score * settings.LEVENSHTEIN_WEIGHT:.3f}")
    print(f"  加权得分: {weighted_score:.3f}")
    
    print("\n🎯 类型匹配影响:")
    
    # 类型匹配情况
    type_match_score = weighted_score * settings.TYPE_MATCH_BONUS
    print(f"  类型匹配: {weighted_score:.3f} × {settings.TYPE_MATCH_BONUS:.1f} = {type_match_score:.3f}")
    
    # 类型不匹配情况
    type_mismatch_score = weighted_score * settings.TYPE_MISMATCH_PENALTY
    print(f"  类型不匹配: {weighted_score:.3f} × {settings.TYPE_MISMATCH_PENALTY:.1f} = {type_mismatch_score:.3f}")
    
    # 类型信息缺失情况
    type_neutral_score = weighted_score * 1.0
    print(f"  类型信息缺失: {weighted_score:.3f} × 1.0 = {type_neutral_score:.3f}")
    
    print("\n📈 对比分析:")
    print(f"  类型匹配 vs 类型不匹配: {type_match_score / type_mismatch_score:.2f}x")
    print(f"  类型匹配 vs 中性: {type_match_score / type_neutral_score:.2f}x")
    print(f"  类型不匹配 vs 中性: {type_mismatch_score / type_neutral_score:.2f}x")
    
    print("\n✅ 公式验证:")
    print("  最终得分 = (BGE×0.4 + CrossEncoder×0.3 + Fuzz×0.2 + Levenshtein×0.1) × type_multiplier")
    print("  其中 type_multiplier:")
    print(f"    - 类型匹配: {settings.TYPE_MATCH_BONUS}")
    print(f"    - 类型不匹配: {settings.TYPE_MISMATCH_PENALTY}")
    print("    - 类型信息缺失: 1.0")

if __name__ == "__main__":
    verify_formula() 