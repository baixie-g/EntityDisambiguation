"""
数据库服务管理器 - 统一管理Neo4j实体存储和SQLite历史记录
"""
import logging
from typing import List, Optional

from models import Entity, DisambiguationHistory
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器 - 统一管理实体存储和历史记录"""
    
    def __init__(self):
        self.neo4j_service = None
        self.history_service = None
        self.init_services()
    
    def init_services(self):
        """初始化数据库服务"""
        # 初始化SQLite历史记录服务
        try:
            from .database import history_db_service
            self.history_service = history_db_service
            logger.info("✅ SQLite历史记录服务初始化成功")
        except Exception as e:
            logger.error(f"❌ SQLite历史记录服务初始化失败: {e}")
            raise e
        
        # 初始化Neo4j实体存储服务
        try:
            from .neo4j_database import create_neo4j_db_service
            self.neo4j_service = create_neo4j_db_service()
            if self.neo4j_service:
                logger.info("✅ Neo4j实体存储服务初始化成功")
            else:
                logger.error("❌ Neo4j实体存储服务初始化失败")
                raise Exception("Neo4j服务创建失败")
        except ImportError as e:
            logger.error(f"❌ Neo4j驱动未安装: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ Neo4j服务初始化失败: {e}")
            raise e
    
    # === 实体存储相关方法 (Neo4j) ===
    def save_entity(self, entity: Entity) -> bool:
        """保存实体到Neo4j"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return False
        return self.neo4j_service.save_entity(entity)
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """从Neo4j获取实体"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return None
        return self.neo4j_service.get_entity(entity_id)
    
    def get_all_entities(self) -> List[Entity]:
        """从Neo4j获取所有实体"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return []
        return self.neo4j_service.get_all_entities()
    
    def search_entities(self, query: str, entity_type: Optional[str] = None, limit: int = 100) -> List[Entity]:
        """在Neo4j中搜索实体"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return []
        return self.neo4j_service.search_entities(query, entity_type, limit)
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """从Neo4j根据类型获取实体"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return []
        return self.neo4j_service.get_entities_by_type(entity_type)
    
    def get_entity_count(self) -> int:
        """获取Neo4j中的实体数量"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return 0
        return self.neo4j_service.get_entity_count()
    
    def create_entity_relationship(self, entity1_id: str, entity2_id: str, relationship_type: str, properties: Optional[dict] = None) -> bool:
        """在Neo4j中创建实体关系"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return False
        return self.neo4j_service.create_entity_relationship(entity1_id, entity2_id, relationship_type, properties)
    
    def get_related_entities(self, entity_id: str, relationship_type: Optional[str] = None) -> List[Entity]:
        """从Neo4j获取相关实体"""
        if not self.neo4j_service:
            logger.error("Neo4j服务未初始化")
            return []
        return self.neo4j_service.get_related_entities(entity_id, relationship_type)
    
    # === 历史记录相关方法 (SQLite) ===
    def save_disambiguation_history(self, history: DisambiguationHistory) -> bool:
        """保存消歧历史到SQLite"""
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return False
        return self.history_service.save_disambiguation_history(history)
    
    def get_disambiguation_history(self, limit: int = 100) -> List[DisambiguationHistory]:
        """从SQLite获取消歧历史"""
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return []
        return self.history_service.get_disambiguation_history(limit)
    
    def get_history_count(self) -> int:
        """获取SQLite中的历史记录数量"""
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return 0
        return self.history_service.get_history_count()
    
    def get_decision_stats(self) -> dict:
        """获取决策统计信息"""
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return {}
        return self.history_service.get_decision_stats()
    
    def clear_history(self) -> bool:
        """清空历史记录"""
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return False
        return self.history_service.clear_history()
    
    # === 服务管理方法 ===
    def close(self):
        """关闭数据库连接"""
        if self.neo4j_service:
            self.neo4j_service.close()
        logger.info("数据库连接已关闭")
    
    def init_databases(self):
        """初始化数据库"""
        if self.history_service:
            self.history_service.init_database()
        if self.neo4j_service:
            self.neo4j_service.init_database()
    
    def is_ready(self) -> bool:
        """检查数据库服务是否就绪"""
        return self.neo4j_service is not None and self.history_service is not None

# 全局数据库管理器实例
db_manager = DatabaseManager() 