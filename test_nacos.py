#!/usr/bin/env python3
"""
测试Nacos配置解析功能 - 轻量级实现
"""
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.nacos_config import nacos_config_service

def test_nacos_config():
    """测试Nacos配置解析"""
    print("🔧 测试Nacos配置解析...")
    
    # 检查Nacos服务可用性
    if nacos_config_service.is_available():
        print("✅ Nacos服务可用")
    else:
        print("⚠️ Nacos服务不可用，将使用本地配置")
    
    # 测试配置解析
    neo4j_configs = nacos_config_service.parse_neo4j_datasources()
    
    print(f"📋 解析结果:")
    print(f"   数据源数量: {len(neo4j_configs)}")
    
    for key, config in neo4j_configs.items():
        print(f"   {key}:")
        print(f"     名称: {config.get('name', 'N/A')}")
        print(f"     主机: {config.get('host', 'N/A')}:{config.get('port', 'N/A')}")
        print(f"     数据库: {config.get('database', 'N/A')}")
        print(f"     用户: {config.get('user', 'N/A')}")
        print(f"     URI: {config.get('uri', 'N/A')}")
    
    # 测试默认键名
    default_key = nacos_config_service.get_default_database_key()
    print(f"🔑 默认数据库键名: {default_key}")
    
    # 测试配置刷新
    print("\n🔄 测试配置刷新...")
    try:
        refreshed_configs = nacos_config_service.refresh_config()
        print(f"✅ 配置刷新成功，数据源数量: {len(refreshed_configs)}")
    except Exception as e:
        print(f"❌ 配置刷新失败: {e}")
    
    return neo4j_configs

if __name__ == "__main__":
    try:
        configs = test_nacos_config()
        if configs:
            print("\n✅ 测试成功")
        else:
            print("\n⚠️ 未获取到配置，检查Nacos连接或使用本地配置")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
