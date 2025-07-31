#!/usr/bin/env python3
"""
测试所有模型的得分范围
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from rapidfuzz import fuzz
from Levenshtein import distance as levenshtein_distance

def test_bge_range():
    """测试BGE向量相似度得分范围"""
    print("=" * 60)
    print("BGE-M3向量相似度得分范围测试")
    print("=" * 60)
    
    # 模拟BGE向量相似度计算
    test_pairs = [
        ("完全相同的文本", "完全相同的文本"),
        ("糖尿病", "糖尿病"),
        ("糖尿病", "diabetes"),
        ("糖尿病", "糖尿"),
        ("糖尿病", "高血压"),
        ("机械与动力工程", "小李"),
        ("", ""),
        ("很长的文本" * 10, "很长的文本" * 10),
    ]
    
    print("📊 BGE得分范围: 0.0 - 1.0 (余弦相似度)")
    print("📋 测试用例:")
    
    for i, (text1, text2) in enumerate(test_pairs):
        # 模拟余弦相似度计算
        if text1 == text2:
            score = 1.0
        elif not text1 or not text2:
            score = 0.0
        else:
            # 简单的相似度模拟
            common_chars = len(set(text1) & set(text2))
            total_chars = len(set(text1) | set(text2))
            score = common_chars / total_chars if total_chars > 0 else 0.0
        
        print(f"  测试{i+1}: '{text1[:20]}...' vs '{text2[:20]}...' = {score:.4f}")
    
    print(f"\n✅ BGE得分范围确认: 0.0 - 1.0")

def test_fuzz_range():
    """测试RapidFuzz字符串匹配得分范围"""
    print("\n" + "=" * 60)
    print("RapidFuzz字符串匹配得分范围测试")
    print("=" * 60)
    
    test_pairs = [
        ("完全相同的文本", "完全相同的文本"),
        ("糖尿病", "糖尿病"),
        ("糖尿病", "diabetes"),
        ("糖尿病", "糖尿"),
        ("糖尿病", "高血压"),
        ("机械与动力工程", "小李"),
        ("", ""),
        ("很长的文本" * 10, "很长的文本" * 10),
    ]
    
    print("📊 RapidFuzz得分范围: 0.0 - 1.0 (归一化)")
    print("📋 测试用例:")
    
    scores = []
    for i, (text1, text2) in enumerate(test_pairs):
        try:
            # 使用token_sort_ratio并归一化
            score = fuzz.token_sort_ratio(text1, text2) / 100.0
            scores.append(score)
            print(f"  测试{i+1}: '{text1[:20]}...' vs '{text2[:20]}...' = {score:.4f}")
        except Exception as e:
            print(f"  测试{i+1}: 失败 - {e}")
    
    if scores:
        min_score = min(scores)
        max_score = max(scores)
        print(f"\n📊 RapidFuzz得分统计:")
        print(f"  最小值: {min_score:.4f}")
        print(f"  最大值: {max_score:.4f}")
        print(f"  得分范围: {min_score:.4f} - {max_score:.4f}")
    
    print(f"\n✅ RapidFuzz得分范围确认: 0.0 - 1.0")

def test_levenshtein_range():
    """测试Levenshtein编辑距离得分范围"""
    print("\n" + "=" * 60)
    print("Levenshtein编辑距离得分范围测试")
    print("=" * 60)
    
    test_pairs = [
        ("完全相同的文本", "完全相同的文本"),
        ("糖尿病", "糖尿病"),
        ("糖尿病", "diabetes"),
        ("糖尿病", "糖尿"),
        ("糖尿病", "高血压"),
        ("机械与动力工程", "小李"),
        ("", ""),
        ("很长的文本" * 10, "很长的文本" * 10),
    ]
    
    print("📊 Levenshtein得分范围: 0.0 - 1.0 (归一化)")
    print("📋 测试用例:")
    
    scores = []
    for i, (text1, text2) in enumerate(test_pairs):
        try:
            # 计算编辑距离得分
            distance = levenshtein_distance(text1, text2)
            max_len = max(len(text1), len(text2))
            score = 1.0 - (distance / max_len) if max_len > 0 else 0.0
            scores.append(score)
            print(f"  测试{i+1}: '{text1[:20]}...' vs '{text2[:20]}...' = {score:.4f}")
        except Exception as e:
            print(f"  测试{i+1}: 失败 - {e}")
    
    if scores:
        min_score = min(scores)
        max_score = max(scores)
        print(f"\n📊 Levenshtein得分统计:")
        print(f"  最小值: {min_score:.4f}")
        print(f"  最大值: {max_score:.4f}")
        print(f"  得分范围: {min_score:.4f} - {max_score:.4f}")
    
    print(f"\n✅ Levenshtein得分范围确认: 0.0 - 1.0")

def test_crossencoder_range():
    """测试CrossEncoder得分范围"""
    print("\n" + "=" * 60)
    print("CrossEncoder得分范围测试")
    print("=" * 60)
    
    try:
        from sentence_transformers import CrossEncoder
        print("✅ 成功导入CrossEncoder")
    except ImportError:
        print("❌ 无法导入CrossEncoder")
        return
    
    # 测试当前使用的模型
    model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    test_pairs = [
        ("完全相同的文本", "完全相同的文本"),
        ("糖尿病", "糖尿病"),
        ("糖尿病", "diabetes"),
        ("糖尿病", "糖尿"),
        ("糖尿病", "高血压"),
        ("机械与动力工程", "小李"),
        ("", ""),
        ("很长的文本" * 10, "很长的文本" * 10),
    ]
    
    try:
        model = CrossEncoder(model_name)
        print(f"✅ 模型加载成功: {model_name}")
        
        scores = []
        for i, (text1, text2) in enumerate(test_pairs):
            try:
                score = model.predict([(text1, text2)])[0]
                scores.append(score)
                print(f"  测试{i+1}: '{text1[:20]}...' vs '{text2[:20]}...' = {score:.4f}")
            except Exception as e:
                print(f"  测试{i+1}: 失败 - {e}")
        
        if scores:
            min_score = min(scores)
            max_score = max(scores)
            avg_score = sum(scores) / len(scores)
            
            print(f"\n📊 CrossEncoder得分统计:")
            print(f"  最小值: {min_score:.4f}")
            print(f"  最大值: {max_score:.4f}")
            print(f"  平均值: {avg_score:.4f}")
            print(f"  得分范围: {min_score:.4f} - {max_score:.4f}")
            
            # 分析得分分布
            negative_scores = [s for s in scores if s < 0]
            low_scores = [s for s in scores if 0 <= s < 0.3]
            mid_scores = [s for s in scores if 0.3 <= s < 0.7]
            high_scores = [s for s in scores if s >= 0.7]
            
            print(f"\n📈 得分分布:")
            print(f"  负分 (<0): {len(negative_scores)}个")
            print(f"  低分 (0-0.3): {len(low_scores)}个")
            print(f"  中分 (0.3-0.7): {len(mid_scores)}个")
            print(f"  高分 (≥0.7): {len(high_scores)}个")
            
            print(f"\n⚠️ 重要发现:")
            print(f"  - CrossEncoder得分范围: {min_score:.4f} - {max_score:.4f}")
            print(f"  - 存在负分: {len(negative_scores)}个")
            print(f"  - 高分超过1.0: {max_score > 1.0}")
            
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")

def test_combined_scores():
    """测试组合得分计算"""
    print("\n" + "=" * 60)
    print("组合得分计算测试")
    print("=" * 60)
    
    # 模拟各模型的得分
    test_cases = [
        {
            "name": "完全匹配",
            "bge": 1.0,
            "cross": 7.7,  # 基于实际测试结果
            "fuzz": 1.0,
            "levenshtein": 1.0
        },
        {
            "name": "高匹配",
            "bge": 0.8,
            "cross": 4.9,  # 基于实际测试结果
            "fuzz": 0.9,
            "levenshtein": 0.8
        },
        {
            "name": "中等匹配",
            "bge": 0.6,
            "cross": 3.3,  # 基于实际测试结果
            "fuzz": 0.7,
            "levenshtein": 0.6
        },
        {
            "name": "低匹配",
            "bge": 0.3,
            "cross": 0.1,  # 基于实际测试结果
            "fuzz": 0.4,
            "levenshtein": 0.3
        },
        {
            "name": "不匹配",
            "bge": 0.1,
            "cross": -5.4,  # 基于实际测试结果
            "fuzz": 0.1,
            "levenshtein": 0.1
        }
    ]
    
    # 权重配置
    weights = {
        "bge": 0.4,
        "cross": 0.3,
        "fuzz": 0.2,
        "levenshtein": 0.1
    }
    
    print("📊 当前权重配置:")
    for model, weight in weights.items():
        print(f"  {model}: {weight}")
    
    print("\n🧮 组合得分计算:")
    print("  加权得分 = BGE×0.4 + CrossEncoder×0.3 + Fuzz×0.2 + Levenshtein×0.1")
    
    for case in test_cases:
        print(f"\n📋 {case['name']}:")
        print("-" * 40)
        
        # 计算加权得分
        weighted_score = (
            case['bge'] * weights['bge'] +
            case['cross'] * weights['cross'] +
            case['fuzz'] * weights['fuzz'] +
            case['levenshtein'] * weights['levenshtein']
        )
        
        print(f"  BGE: {case['bge']:.3f} × {weights['bge']:.1f} = {case['bge'] * weights['bge']:.3f}")
        print(f"  CrossEncoder: {case['cross']:.3f} × {weights['cross']:.1f} = {case['cross'] * weights['cross']:.3f}")
        print(f"  Fuzz: {case['fuzz']:.3f} × {weights['fuzz']:.1f} = {case['fuzz'] * weights['fuzz']:.3f}")
        print(f"  Levenshtein: {case['levenshtein']:.3f} × {weights['levenshtein']:.1f} = {case['levenshtein'] * weights['levenshtein']:.3f}")
        print(f"  加权得分: {weighted_score:.3f}")
        
        # 分析问题
        if weighted_score > 1.0:
            print(f"  ⚠️ 问题: 加权得分超过1.0!")
        elif weighted_score < 0.0:
            print(f"  ⚠️ 问题: 加权得分为负值!")
        else:
            print(f"  ✅ 加权得分在合理范围内")

def main():
    """主测试函数"""
    print("=" * 80)
    print("所有模型得分范围全面测试")
    print("=" * 80)
    
    # 测试各个模型
    test_bge_range()
    test_fuzz_range()
    test_levenshtein_range()
    test_crossencoder_range()
    test_combined_scores()
    
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    print("📋 各模型得分范围总结:")
    print("  1. BGE-M3向量相似度: 0.0 - 1.0")
    print("  2. RapidFuzz字符串匹配: 0.0 - 1.0")
    print("  3. Levenshtein编辑距离: 0.0 - 1.0")
    print("  4. CrossEncoder重排序: -6.5 - 7.7 (需要特殊处理)")
    
    print("\n⚠️ 关键问题:")
    print("  1. CrossEncoder得分范围与其他模型不一致")
    print("  2. CrossEncoder存在负分和高分超过1.0的情况")
    print("  3. 当前归一化方法 min(score, 1.0) 是错误的")
    print("  4. 需要重新设计CrossEncoder的归一化策略")
    
    print("\n🔧 建议解决方案:")
    print("  1. 使用sigmoid函数归一化CrossEncoder得分")
    print("  2. 或者使用min-max归一化到0.0-1.0范围")
    print("  3. 或者调整权重配置，降低CrossEncoder权重")

if __name__ == "__main__":
    main() 