#!/usr/bin/env python3
"""
Neo4j实体上传脚本 - 用于上传单个实体到Neo4j数据库
"""
import json
import logging
import sys
from datetime import datetime

from models import Entity
from services.neo4j_database import create_neo4j_db_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def upload_entity_from_json(json_data: dict):
    """
    从JSON数据上传实体到Neo4j
    
    Args:
        json_data: 包含实体信息的JSON字典
    
    Returns:
        bool: 是否上传成功
    """
    logger.info("📤 开始上传实体到Neo4j...")
    
    # 创建Neo4j服务
    neo4j_service = create_neo4j_db_service()
    if not neo4j_service:
        logger.error("❌ Neo4j服务创建失败")
        return False

    try:
        entity_data = json_data.get("entity", {})
        
        # 创建实体对象
        entity = Entity(
            name=entity_data["name"],
            type=entity_data.get("type"),  # 改为可选
            aliases=entity_data.get("aliases", []),
            definition=entity_data.get("definition"),
            attributes=entity_data.get("attributes", {}),
            source=entity_data.get("source"),
            create_time=datetime.now()
        )
        
        # 保存到Neo4j
        if neo4j_service.save_entity(entity):
            logger.info(f"✅ 实体 '{entity.name}' 成功上传到Neo4j")
        else:
            logger.error(f"❌ 实体 '{entity.name}' 上传到Neo4j失败")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ 上传实体失败: {e}")
        return False

    finally:
        if neo4j_service:
            neo4j_service.close()

def main():
    """主函数：从标准输入读取JSON数据并上传"""
    logger.info("📥 等待输入JSON实体数据...")
    
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            logger.error("❌ 输入为空")
            return False
        
        json_data = json.loads(input_data)
        
        # 上传实体
        if upload_entity_from_json(json_data):
            logger.info("🎉 实体上传完成！")
            return True
        else:
            return False
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON格式错误: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)