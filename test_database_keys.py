#!/usr/bin/env python3
"""
测试数据库键名状态
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.database_factory import db_manager
from services.nacos_config import nacos_config_service

def test_database_keys():
    """测试数据库键名状态"""
    print("🔍 测试数据库键名状态")
    print("=" * 50)
    
    # 测试Nacos配置
    print("1. Nacos配置状态:")
    print(f"   Nacos可用: {nacos_config_service.is_available()}")
    
    if nacos_config_service.is_available():
        configs = nacos_config_service.parse_neo4j_datasources()
        print(f"   数据源配置: {list(configs.keys())}")
        
        for key, config in configs.items():
            print(f"     {key}: {config.get('name', 'Unknown')} ({config.get('host', 'Unknown')}:{config.get('port', 'Unknown')})")
    
    print()
    
    # 测试数据库管理器
    print("2. 数据库管理器状态:")
    print(f"   默认键名: {db_manager.get_default_key()}")
    print(f"   可用数据库: {db_manager.list_databases()}")
    
    # 测试每个数据库
    for db_key in db_manager.list_databases():
        service = db_manager.get_service(db_key)
        if service:
            print(f"   数据库 {db_key}:")
            print(f"     名称: {getattr(service, 'db_name', 'Unknown')}")
            print(f"     主机: {getattr(service, 'host', 'Unknown')}")
            print(f"     端口: {getattr(service, 'port', 'Unknown')}")
            print(f"     实体数量: {service.get_entity_count()}")
        else:
            print(f"   数据库 {db_key}: 服务未找到")
    
    print()
    
    # 测试向量化服务
    print("3. 向量化服务状态:")
    from services.vectorization import vectorization_service
    
    # 测试默认键名获取
    db_manager_instance = vectorization_service._get_db_manager()
    if hasattr(db_manager_instance, 'get_default_key'):
        default_key = db_manager_instance.get_default_key()
        print(f"   默认键名: {default_key}")
        
        # 测试索引状态
        for db_key in db_manager.list_databases():
            stats = vectorization_service.get_index_stats(db_key)
            print(f"   数据库 {db_key} 索引状态:")
            print(f"     模型加载: {stats['model_loaded']}")
            print(f"     索引加载: {stats['index_loaded']}")
            print(f"     实体数量: {stats['entity_count']}")
            print(f"     索引维度: {stats['index_dimension']}")
            print(f"     数据库键: {stats['database_key']}")
    else:
        print("   无法获取默认键名")
    
    print()
    print("✅ 测试完成")

if __name__ == "__main__":
    test_database_keys()
