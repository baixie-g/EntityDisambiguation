#!/usr/bin/env python3
"""
测试数据库路由问题
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.disambiguation import DisambiguationService
from services.vectorization import vectorization_service
from models import Entity

def test_database_routing():
    """测试数据库路由问题"""
    print("🔍 测试数据库路由问题")
    print("=" * 50)
    
    # 创建消歧服务实例
    disambiguation_service = DisambiguationService()
    
    # 创建测试实体
    test_entity = Entity(
        name="测试实体",
        type="Person",
        aliases=["测试"],
        definition="这是一个测试实体"
    )
    
    print("1. 测试不指定数据库键名:")
    try:
        candidates = disambiguation_service.match_candidates(test_entity, top_k=5)
        print(f"   结果: 找到 {len(candidates)} 个候选")
    except Exception as e:
        print(f"   错误: {e}")
    
    print()
    
    print("2. 测试指定数据库键名 '1':")
    try:
        candidates = disambiguation_service.match_candidates(test_entity, top_k=5, db_key="1")
        print(f"   结果: 找到 {len(candidates)} 个候选")
    except Exception as e:
        print(f"   错误: {e}")
    
    print()
    
    print("3. 测试指定数据库键名 '2':")
    try:
        candidates = disambiguation_service.match_candidates(test_entity, top_k=5, db_key="2")
        print(f"   结果: 找到 {len(candidates)} 个候选")
    except Exception as e:
        print(f"   错误: {e}")
    
    print()
    
    print("4. 测试向量化服务直接调用:")
    try:
        # 测试向量化服务的默认键名获取
        db_manager = vectorization_service._get_db_manager()
        if hasattr(db_manager, 'get_default_key'):
            default_key = db_manager.get_default_key()
            print(f"   默认键名: {default_key}")
            
            # 测试搜索相似实体
            similar_entities = vectorization_service.search_similar_entities(test_entity, top_k=5)
            print(f"   搜索结果: 找到 {len(similar_entities)} 个相似实体")
        else:
            print("   无法获取默认键名")
    except Exception as e:
        print(f"   错误: {e}")
    
    print()
    print("✅ 测试完成")

if __name__ == "__main__":
    test_database_routing()
