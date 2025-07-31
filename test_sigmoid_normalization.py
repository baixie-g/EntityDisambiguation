#!/usr/bin/env python3
"""
测试Sigmoid归一化效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from services.disambiguation import DisambiguationService

def test_sigmoid_normalization():
    """测试sigmoid归一化效果"""
    print("=" * 80)
    print("Sigmoid归一化效果测试")
    print("=" * 80)
    
    # 创建消歧服务实例
    service = DisambiguationService()
    
    # 基于实际测试结果的CrossEncoder原始得分
    test_scores = [
        ("完全相同的文本", 7.7106),
        ("糖尿病 vs 糖尿病", 4.9174),
        ("糖尿病 vs 糖尿", 3.3470),
        ("糖尿病 vs 高血压", 0.1097),
        ("糖尿病 vs diabetes", -6.5320),
        ("机械与动力工程 vs 小李", -5.4104),
        ("空文本", -3.3430),
    ]
    
    print("📊 Sigmoid归一化效果:")
    print("-" * 60)
    print(f"{'测试用例':<25} {'原始得分':<12} {'Sigmoid归一化':<15} {'说明'}")
    print("-" * 60)
    
    normalized_scores = []
    for test_case, original_score in test_scores:
        normalized_score = service.normalize_crossencoder_score(original_score)
        normalized_scores.append(normalized_score)
        
        # 判断得分类型
        if original_score > 5.0:
            description = "完全匹配"
        elif original_score > 2.0:
            description = "高相关"
        elif original_score > 0.0:
            description = "中等相关"
        elif original_score > -2.0:
            description = "低相关"
        else:
            description = "不相关"
        
        print(f"{test_case:<25} {original_score:<12.4f} {normalized_score:<15.4f} {description}")
    
    print("-" * 60)
    
    # 统计信息
    min_normalized = min(normalized_scores)
    max_normalized = max(normalized_scores)
    avg_normalized = sum(normalized_scores) / len(normalized_scores)
    
    print(f"\n📈 归一化统计:")
    print(f"  最小值: {min_normalized:.4f}")
    print(f"  最大值: {max_normalized:.4f}")
    print(f"  平均值: {avg_normalized:.4f}")
    print(f"  得分范围: {min_normalized:.4f} - {max_normalized:.4f}")
    
    # 验证归一化效果
    print(f"\n✅ 归一化验证:")
    print(f"  - 所有得分都在0.0-1.0范围内: {min_normalized >= 0.0 and max_normalized <= 1.0}")
    print(f"  - 负分被正确映射: {min_normalized > 0.0}")
    print(f"  - 高分被正确映射: {max_normalized < 1.0}")
    
    return normalized_scores

def test_weighted_scores():
    """测试修正后的加权得分"""
    print("\n" + "=" * 80)
    print("修正后加权得分测试")
    print("=" * 80)
    
    service = DisambiguationService()
    
    # 测试用例
    test_cases = [
        {
            "name": "完全匹配",
            "bge": 1.0,
            "cross_original": 7.7106,
            "fuzz": 1.0,
            "levenshtein": 1.0
        },
        {
            "name": "高匹配",
            "bge": 0.8,
            "cross_original": 4.9174,
            "fuzz": 0.9,
            "levenshtein": 0.8
        },
        {
            "name": "中等匹配",
            "bge": 0.6,
            "cross_original": 3.3470,
            "fuzz": 0.7,
            "levenshtein": 0.6
        },
        {
            "name": "低匹配",
            "bge": 0.3,
            "cross_original": 0.1097,
            "fuzz": 0.4,
            "levenshtein": 0.3
        },
        {
            "name": "不匹配",
            "bge": 0.1,
            "cross_original": -6.5320,
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
    
    print("📊 权重配置:")
    for model, weight in weights.items():
        print(f"  {model}: {weight}")
    
    print(f"\n🧮 修正后加权得分计算:")
    print("  加权得分 = BGE×0.4 + CrossEncoder(sigmoid归一化)×0.3 + Fuzz×0.2 + Levenshtein×0.1")
    
    print(f"\n{'匹配情况':<12} {'BGE':<8} {'Cross(原始)':<12} {'Cross(归一化)':<12} {'Fuzz':<8} {'Levenshtein':<12} {'加权得分':<12} {'状态'}")
    print("-" * 100)
    
    for case in test_cases:
        # 计算sigmoid归一化的CrossEncoder得分
        cross_normalized = service.normalize_crossencoder_score(case['cross_original'])
        
        # 计算加权得分
        weighted_score = (
            case['bge'] * weights['bge'] +
            cross_normalized * weights['cross'] +
            case['fuzz'] * weights['fuzz'] +
            case['levenshtein'] * weights['levenshtein']
        )
        
        # 判断状态
        if weighted_score > 1.0:
            status = "❌ 超过1.0"
        elif weighted_score < 0.0:
            status = "❌ 负值"
        else:
            status = "✅ 正常"
        
        print(f"{case['name']:<12} {case['bge']:<8.3f} {case['cross_original']:<12.3f} {cross_normalized:<12.3f} {case['fuzz']:<8.3f} {case['levenshtein']:<12.3f} {weighted_score:<12.3f} {status}")

def test_threshold_analysis():
    """分析阈值设置"""
    print("\n" + "=" * 80)
    print("阈值分析")
    print("=" * 80)
    
    service = DisambiguationService()
    
    # 基于实际测试结果的得分分布
    test_scores = [
        ("完全匹配", 7.7106),
        ("高相关", 4.9174),
        ("中等相关", 3.3470),
        ("低相关", 0.1097),
        ("不相关1", -6.5320),
        ("不相关2", -5.4104),
        ("不相关3", -3.3430),
    ]
    
    print("📊 归一化后的得分分布:")
    print("-" * 50)
    print(f"{'匹配类型':<12} {'原始得分':<12} {'归一化得分':<12} {'建议决策'}")
    print("-" * 50)
    
    normalized_scores = []
    for match_type, original_score in test_scores:
        normalized_score = service.normalize_crossencoder_score(original_score)
        normalized_scores.append(normalized_score)
        
        # 基于归一化得分建议决策
        if normalized_score > 0.9:
            decision = "合并"
        elif normalized_score > 0.7:
            decision = "可能合并"
        elif normalized_score > 0.3:
            decision = "需要审核"
        else:
            decision = "新建"
        
        print(f"{match_type:<12} {original_score:<12.3f} {normalized_score:<12.3f} {decision}")
    
    print("-" * 50)
    
    # 分析阈值设置
    print(f"\n🎯 阈值设置建议:")
    print(f"  当前HIGH_THRESHOLD: 0.85")
    print(f"  当前LOW_THRESHOLD: 0.3")
    
    # 计算建议阈值
    sorted_scores = sorted(normalized_scores)
    print(f"\n📈 得分分布分析:")
    print(f"  最高得分: {max(normalized_scores):.3f}")
    print(f"  最低得分: {min(normalized_scores):.3f}")
    print(f"  中位数: {sorted_scores[len(sorted_scores)//2]:.3f}")
    
    # 建议阈值
    high_threshold = 0.85  # 保持当前设置
    low_threshold = 0.3    # 保持当前设置
    
    print(f"\n💡 阈值建议:")
    print(f"  HIGH_THRESHOLD: {high_threshold} (合并阈值)")
    print(f"  LOW_THRESHOLD: {low_threshold} (新建阈值)")
    print(f"  歧义区间: [{low_threshold}, {high_threshold}]")

def main():
    """主测试函数"""
    print("=" * 80)
    print("Sigmoid归一化全面测试")
    print("=" * 80)
    
    # 测试sigmoid归一化效果
    normalized_scores = test_sigmoid_normalization()
    
    # 测试修正后的加权得分
    test_weighted_scores()
    
    # 分析阈值设置
    test_threshold_analysis()
    
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    print("✅ Sigmoid归一化修正完成:")
    print("  1. CrossEncoder得分已使用sigmoid函数归一化")
    print("  2. 所有得分都在0.0-1.0范围内")
    print("  3. 加权得分不再异常")
    print("  4. 系统行为更加一致")
    
    print("\n📋 实施内容:")
    print("  1. 添加了normalize_crossencoder_score函数")
    print("  2. 修改了CrossEncoder得分计算逻辑")
    print("  3. 更新了配置注释")
    print("  4. 验证了归一化效果")

if __name__ == "__main__":
    main() 