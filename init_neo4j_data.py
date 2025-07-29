#!/usr/bin/env python3
"""
Neo4j数据初始化脚本 - 专门用于初始化Neo4j实体数据
"""
import json
import logging
from pathlib import Path
from datetime import datetime

from models import Entity, EntityType
from services.neo4j_database import create_neo4j_db_service
from services.vectorization import vectorization_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_neo4j_entities():
    """初始化Neo4j实体数据"""
    logger.info("🚀 开始初始化Neo4j实体数据...")
    
    # 创建Neo4j服务
    neo4j_service = create_neo4j_db_service()
    if not neo4j_service:
        logger.error("❌ Neo4j服务创建失败")
        return False
    
    # 读取示例数据文件
    sample_file = Path("data/sample_entities.json")
    if not sample_file.exists():
        logger.error(f"示例数据文件不存在: {sample_file}")
        return False
    
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        
        # 转换为实体对象并保存到Neo4j
        entities = []
        for item in sample_data:
            entity = Entity(
                id=item.get('id'),
                name=item['name'],
                type=EntityType(item['type']),
                aliases=item.get('aliases', []),
                definition=item.get('definition'),
                attributes=item.get('attributes', {}),
                source=item.get('source'),
                create_time=datetime.fromisoformat(item['create_time']) if item.get('create_time') else datetime.now()
            )
            entities.append(entity)
            
            # 保存到Neo4j
            if neo4j_service.save_entity(entity):
                logger.info(f"✅ 实体保存到Neo4j成功: {entity.name}")
            else:
                logger.error(f"❌ 实体保存到Neo4j失败: {entity.name}")
        
        logger.info(f"🎉 Neo4j实体数据初始化完成，共加载 {len(entities)} 个实体")
        
        # 构建向量索引
        logger.info("🔄 开始构建向量索引...")
        if vectorization_service.build_faiss_index(entities):
            logger.info("🎉 向量索引构建完成")
        else:
            logger.error("❌ 向量索引构建失败")
        
        # 关闭Neo4j连接
        neo4j_service.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 初始化Neo4j实体数据失败: {e}")
        if neo4j_service:
            neo4j_service.close()
        return False

def main():
    """主函数"""
    logger.info("🚀 开始初始化实体消歧服务数据...")
    
    # 初始化Neo4j实体数据
    if not init_neo4j_entities():
        logger.error("❌ Neo4j实体数据初始化失败")
        return False
    
    logger.info("🎉 数据初始化完成！")
    logger.info("现在可以启动服务: python main.py")
    
    return True

if __name__ == "__main__":
    main() 