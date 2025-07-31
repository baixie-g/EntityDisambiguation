#!/usr/bin/env python3
"""
测试CrossEncoder的实际得分范围
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_crossencoder_range():
    """测试CrossEncoder的实际得分范围"""
    
    print("=" * 80)
    print("CrossEncoder得分范围测试")
    print("=" * 80)
    
    # 尝试导入CrossEncoder
    try:
        from sentence_transformers import CrossEncoder
        print("✅ 成功导入CrossEncoder")
    except ImportError:
        print("❌ 无法导入CrossEncoder，sentence-transformers未安装")
        return
    
    # 测试不同的CrossEncoder模型
    test_models = [
        "cross-encoder/ms-marco-MiniLM-L-6-v2",  # 当前使用的模型
        "cross-encoder/stsb-roberta-base",       # 另一个常用模型
        "cross-encoder/quora-distilroberta-base" # 问答匹配模型
    ]
    
    # 测试用例
    test_pairs = [
        ("完全相同的文本", "完全相同的文本"),  # 应该得到最高分
        ("糖尿病", "糖尿病"),                  # 实体名称完全匹配
        ("糖尿病", "diabetes"),                # 中英文匹配
        ("糖尿病", "糖尿"),                    # 部分匹配
        ("糖尿病", "高血压"),                  # 完全不相关
        ("机械与动力工程", "小李"),            # 完全不相关
        ("", ""),                              # 空字符串
        ("很长的文本" * 10, "很长的文本" * 10), # 长文本
    ]
    
    for model_name in test_models:
        print(f"\n🔍 测试模型: {model_name}")
        print("-" * 60)
        
        try:
            # 加载模型
            model = CrossEncoder(model_name)
            print(f"✅ 模型加载成功")
            
            # 测试得分范围
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
                
                print(f"\n📊 得分统计:")
                print(f"  最小值: {min_score:.4f}")
                print(f"  最大值: {max_score:.4f}")
                print(f"  平均值: {avg_score:.4f}")
                print(f"  得分范围: {min_score:.4f} - {max_score:.4f}")
                
                # 分析得分分布
                print(f"\n📈 得分分布:")
                low_scores = [s for s in scores if s < 0.3]
                mid_scores = [s for s in scores if 0.3 <= s < 0.7]
                high_scores = [s for s in scores if s >= 0.7]
                
                print(f"  低分 (<0.3): {len(low_scores)}个")
                print(f"  中分 (0.3-0.7): {len(mid_scores)}个")
                print(f"  高分 (≥0.7): {len(high_scores)}个")
                
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
    
    print("\n" + "=" * 80)
    print("CrossEncoder得分范围总结")
    print("=" * 80)
    
    print("📋 重要发现:")
    print("1. CrossEncoder的得分范围通常不是0.0-1.0")
    print("2. 不同模型的得分范围可能不同")
    print("3. 常见的得分范围:")
    print("   - ms-marco模型: 通常0.0-1.0或更高")
    print("   - stsb模型: 通常-1.0到1.0")
    print("   - quora模型: 通常0.0-1.0")
    
    print("\n⚠️ 对当前系统的影响:")
    print("1. 如果CrossEncoder得分超过1.0，加权得分可能超过1.0")
    print("2. 需要检查是否需要归一化CrossEncoder得分")
    print("3. 可能需要调整权重配置")

if __name__ == "__main__":
    test_crossencoder_range() 