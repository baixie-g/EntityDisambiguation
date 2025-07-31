#!/usr/bin/env python3
"""
初始化脚本 - 加载示例数据和构建索引
"""
import json
import logging
from pathlib import Path
from datetime import datetime

from models import Entity
from services import db_manager, vectorization_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_sample_entities():
    """加载示例实体数据"""
    logger.info("🔄 开始加载示例实体数据...")
    
    # 读取示例数据文件
    sample_file = Path("data/sample_entities.json")
    if not sample_file.exists():
        logger.error(f"示例数据文件不存在: {sample_file}")
        return False
    
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        
        # 转换为实体对象并保存
        entities = []
        for item in sample_data:
            entity = Entity(
                id=item.get('id'),
                name=item['name'],
                type=item.get('type'),  # 直接使用字符串
                aliases=item.get('aliases', []),
                definition=item.get('definition'),
                attributes=item.get('attributes', {}),
                source=item.get('source'),
                create_time=datetime.fromisoformat(item['create_time']) if item.get('create_time') else datetime.now()
            )
            entities.append(entity)
            
            # 保存到数据库
            if db_manager.save_entity(entity):
                logger.info(f"✅ 实体保存成功: {entity.name}")
            else:
                logger.error(f"❌ 实体保存失败: {entity.name}")
        
        logger.info(f"🎉 示例数据加载完成，共加载 {len(entities)} 个实体")
        return True
        
    except Exception as e:
        logger.error(f"❌ 加载示例数据失败: {e}")
        return False

def build_vector_index():
    """构建向量索引"""
    logger.info("🔄 开始构建向量索引...")
    
    try:
        # 获取所有实体
        entities = db_manager.get_all_entities()
        
        if not entities:
            logger.warning("⚠️ 没有找到实体，请先加载数据")
            return False
        
        # 构建FAISS索引
        if vectorization_service.build_faiss_index(entities):
            logger.info("🎉 向量索引构建完成")
            return True
        else:
            logger.error("❌ 向量索引构建失败")
            return False
            
    except Exception as e:
        logger.error(f"❌ 构建向量索引失败: {e}")
        return False

def test_disambiguation():
    """测试消歧功能"""
    logger.info("🔄 开始测试消歧功能...")
    
    try:
        from services import disambiguation_service
        
        # 创建测试实体
        test_entity = Entity(
            name="糖尿病",
            type="疾病",  # 可以保持使用字符串
            aliases=["diabetes"],
            definition="糖尿病是一组以高血糖为特征的代谢性疾病"
        )
        
        # 测试自动决策
        result = disambiguation_service.auto_decide(test_entity)
        
        logger.info(f"✅ 消歧测试完成")
        logger.info(f"   决策结果: {result.decision.value}")
        logger.info(f"   推理过程: {result.reasoning}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 消歧测试失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始初始化实体消歧服务...")
    
    # 步骤1: 初始化数据库
    logger.info("📊 初始化数据库...")
    db_manager.init_databases()
    
    # 步骤2: 加载示例数据
    if not load_sample_entities():
        logger.error("❌ 加载示例数据失败，退出")
        return False
    
    # 步骤3: 构建向量索引
    if not build_vector_index():
        logger.error("❌ 构建向量索引失败，退出")
        return False
    
    # # 步骤4: 测试消歧功能
    # if not test_disambiguation():
    #     logger.error("❌ 测试消歧功能失败")
    #     return False
    
    # logger.info("🎉 初始化完成！现在可以启动服务了")
    # logger.info("启动命令: python main.py")
    
    return True

if __name__ == "__main__":
    main() 


