#!/usr/bin/env python3
"""
数据库状态检查脚本 - 检查Neo4j和SQLite的连接状态
"""
import logging
import sys
from datetime import datetime

from config.settings import settings
from services.database_factory import db_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_neo4j_status():
    """检查Neo4j连接状态"""
    logger.info("🔍 检查Neo4j连接状态...")
    
    try:
        # 检查Neo4j服务是否可用
        if not db_manager.neo4j_service:
            logger.error("❌ Neo4j服务未初始化")
            return False
        
        # 检查实体数量
        entity_count = db_manager.get_entity_count()
        logger.info(f"✅ Neo4j连接正常，实体数量: {entity_count}")
        
        # 获取一些示例实体
        entities = db_manager.get_all_entities()
        if entities:
            logger.info(f"   示例实体: {entities[0].name} ({entities[0].type.value})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Neo4j连接失败: {e}")
        return False

def check_sqlite_status():
    """检查SQLite连接状态"""
    logger.info("🔍 检查SQLite连接状态...")
    
    try:
        # 检查SQLite服务是否可用
        if not db_manager.history_service:
            logger.error("❌ SQLite历史记录服务未初始化")
            return False
        
        # 检查历史记录数量
        history_count = db_manager.get_history_count()
        logger.info(f"✅ SQLite连接正常，历史记录数量: {history_count}")
        
        # 获取决策统计
        stats = db_manager.get_decision_stats()
        if stats:
            logger.info(f"   决策统计: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ SQLite连接失败: {e}")
        return False

def check_database_configuration():
    """检查数据库配置"""
    logger.info("🔍 检查数据库配置...")
    
    logger.info(f"Neo4j配置:")
    logger.info(f"  URI: {settings.NEO4J_URI}")
    logger.info(f"  用户: {settings.NEO4J_USER}")
    logger.info(f"  数据库: {settings.NEO4J_DATABASE}")
    
    logger.info(f"SQLite配置:")
    logger.info(f"  路径: {settings.SQLITE_DATABASE_PATH}")
    
    return True

def main():
    """主函数"""
    logger.info("🚀 开始检查数据库状态...")
    logger.info("=" * 60)
    
    # 检查配置
    check_database_configuration()
    logger.info("=" * 60)
    
    # 检查数据库管理器状态
    if not db_manager.is_ready():
        logger.error("❌ 数据库管理器未就绪")
        return False
    
    logger.info("✅ 数据库管理器已就绪")
    logger.info("=" * 60)
    
    # 检查Neo4j状态
    neo4j_ok = check_neo4j_status()
    logger.info("=" * 60)
    
    # 检查SQLite状态
    sqlite_ok = check_sqlite_status()
    logger.info("=" * 60)
    
    # 总结
    if neo4j_ok and sqlite_ok:
        logger.info("🎉 所有数据库连接正常！")
        logger.info("📊 数据库架构:")
        logger.info("   Neo4j: 实体存储 (主要业务数据)")
        logger.info("   SQLite: 历史记录存储 (消歧决策历史)")
        return True
    else:
        logger.error("❌ 数据库连接存在问题")
        if not neo4j_ok:
            logger.error("   Neo4j连接失败 - 请检查Neo4j服务是否启动")
        if not sqlite_ok:
            logger.error("   SQLite连接失败 - 请检查文件权限")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 