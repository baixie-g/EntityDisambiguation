"""
数据库服务管理器 - 统一管理多个Neo4j实体存储和SQLite历史记录
"""
import logging
from typing import List, Optional, Dict

from models import Entity, DisambiguationHistory
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器 - 支持多Neo4j实例的实体存储与单SQLite历史记录"""
    
    def __init__(self):
        self.neo4j_services: Dict[str, object] = {}
        self.history_service = None
        self.default_key: str = settings.DEFAULT_NEO4J_KEY
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
        
        # 初始化多个Neo4j实体存储服务
        try:
            from .neo4j_database import Neo4jDatabaseService
        except ImportError as e:
            logger.error(f"❌ Neo4j驱动未安装: {e}")
            raise e
        
        # 尝试从Nacos获取数据库配置
        neo4j_configs = self._get_neo4j_configs()
        
        created = []
        for key, conf in neo4j_configs.items():
            try:
                service = Neo4jDatabaseService(
                    uri=conf.get("uri"),
                    user=conf.get("user"),
                    password=conf.get("password"),
                    database_name=conf.get("database"),
                    db_info=conf  # 传递完整的数据库信息
                )
                self.neo4j_services[key] = service
                created.append(key)
                logger.info(f"✅ Neo4j服务创建成功[{key}]: {conf.get('name', 'Unknown')} ({conf.get('host', 'unknown')}:{conf.get('port', 'unknown')})")
            except Exception as e:
                logger.error(f"❌ Neo4j服务创建失败[{key}]: {e}")
        
        if not self.neo4j_services:
            # 回退到单库配置
            try:
                service = Neo4jDatabaseService(
                    uri=settings.NEO4J_URI,
                    user=settings.NEO4J_USER,
                    password=settings.NEO4J_PASSWORD,
                    database_name=settings.NEO4J_DATABASE
                )
                self.neo4j_services[self.default_key] = service
                created.append(self.default_key)
                logger.info(f"✅ Neo4j服务创建成功 (回退配置): {self.default_key}")
            except Exception as e:
                logger.error(f"❌ Neo4j实体存储服务初始化失败: {e}")
                raise e
        
        # 更新默认键名
        if created:
            self.default_key = created[0] if 'default' not in created else 'default'
        
        logger.info(f"✅ Neo4j实例初始化完成: {created}, 默认库: {self.default_key}")
    
    def _get_neo4j_configs(self) -> Dict[str, Dict]:
        """获取Neo4j数据库配置（优先从Nacos获取）"""
        try:
            from .nacos_config import nacos_config_service
            if nacos_config_service.is_available():
                logger.info("🔧 从Nacos获取数据库配置")
                configs = nacos_config_service.parse_neo4j_datasources()
                if configs:
                    return configs
                else:
                    logger.warning("⚠️ Nacos配置解析失败，使用本地配置")
            else:
                logger.info("🔧 Nacos不可用，使用本地配置")
        except Exception as e:
            logger.warning(f"⚠️ 获取Nacos配置失败: {e}，使用本地配置")
        
        # 回退到本地配置
        return settings.NEO4J_DATABASES
    
    # === 工具方法 ===
    def get_service(self, db_key: Optional[str] = None):
        key = db_key or self.default_key
        service = self.neo4j_services.get(key)
        if not service:
            logger.error(f"Neo4j服务未找到，key={key}")
            # 如果指定的数据库ID不存在，抛出异常
            if db_key and db_key not in self.neo4j_services:
                raise ValueError(f"数据库ID '{db_key}' 不存在。可用的数据库ID: {list(self.neo4j_services.keys())}")
        return service
    
    def validate_database_key(self, db_key: str) -> bool:
        """验证数据库ID是否有效"""
        return db_key in self.neo4j_services
    
    def get_available_database_keys(self) -> List[str]:
        """获取可用的数据库ID列表"""
        return list(self.neo4j_services.keys())
    
    def list_databases(self) -> List[str]:
        return list(self.neo4j_services.keys())
    
    def get_databases_info(self) -> Dict[str, dict]:
        info = {}
        for key, svc in self.neo4j_services.items():
            try:
                count = svc.get_entity_count()
                # 获取数据库的详细信息
                db_info = {
                    "entity_count": count,
                    "id": key,  # 数据库ID
                    "name": getattr(svc, 'db_name', f'Database {key}'),  # 数据库名称
                    "host": getattr(svc, 'host', 'Unknown'),  # 主机地址
                    "port": getattr(svc, 'port', 0),  # 端口
                    "database": getattr(svc, 'database_name', 'neo4j'),  # 数据库名
                    "status": "connected"  # 连接状态
                }
                info[key] = db_info
            except Exception as e:
                logger.warning(f"获取数据库 {key} 信息失败: {e}")
                info[key] = {
                    "entity_count": 0,
                    "id": key,
                    "name": f'Database {key}',
                    "host": "Unknown",
                    "port": 0,
                    "database": "neo4j",
                    "status": "error"
                }
        return info
    
    def get_default_key(self) -> str:
        return self.default_key
    
    def refresh_nacos_config(self) -> bool:
        """刷新Nacos配置并重新初始化数据库连接"""
        try:
            logger.info("🔄 刷新Nacos配置")
            from .nacos_config import nacos_config_service
            if nacos_config_service.is_available():
                # 关闭现有连接
                self.close()
                # 重新初始化
                self.init_services()
                logger.info("✅ Nacos配置刷新成功")
                return True
            else:
                logger.warning("⚠️ Nacos不可用，无法刷新配置")
                return False
        except Exception as e:
            logger.error(f"❌ 刷新Nacos配置失败: {e}")
            return False
    
    # === 实体存储相关方法 (Neo4j) ===
    def save_entity(self, entity: Entity, db_key: Optional[str] = None) -> bool:
        service = self.get_service(db_key)
        if not service:
            return False
        return service.save_entity(entity)
    
    def get_entity(self, entity_id: str, db_key: Optional[str] = None) -> Optional[Entity]:
        service = self.get_service(db_key)
        if not service:
            return None
        return service.get_entity(entity_id)
    
    def get_all_entities(self, db_key: Optional[str] = None) -> List[Entity]:
        service = self.get_service(db_key)
        if not service:
            return []
        return service.get_all_entities()
    
    def search_entities(self, query: str, entity_type: Optional[str] = None, limit: int = 100, db_key: Optional[str] = None) -> List[Entity]:
        service = self.get_service(db_key)
        if not service:
            return []
        return service.search_entities(query, entity_type, limit)
    
    def get_entities_by_type(self, entity_type: str, db_key: Optional[str] = None) -> List[Entity]:
        service = self.get_service(db_key)
        if not service:
            return []
        return service.get_entities_by_type(entity_type)
    
    def get_entity_count(self, db_key: Optional[str] = None) -> int:
        service = self.get_service(db_key)
        if not service:
            return 0
        return service.get_entity_count()
    
    def create_entity_relationship(self, entity1_id: str, entity2_id: str, relationship_type: str, properties: Optional[dict] = None, db_key: Optional[str] = None) -> bool:
        service = self.get_service(db_key)
        if not service:
            return False
        return service.create_entity_relationship(entity1_id, entity2_id, relationship_type, properties)
    
    def get_related_entities(self, entity_id: str, relationship_type: Optional[str] = None, db_key: Optional[str] = None) -> List[Entity]:
        service = self.get_service(db_key)
        if not service:
            return []
        return service.get_related_entities(entity_id, relationship_type)
    
    # === 历史记录相关方法 (SQLite) ===
    def save_disambiguation_history(self, history: DisambiguationHistory) -> bool:
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return False
        return self.history_service.save_disambiguation_history(history)
    
    def get_disambiguation_history(self, limit: int = 100) -> List[DisambiguationHistory]:
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return []
        return self.history_service.get_disambiguation_history(limit)
    
    def get_history_count(self) -> int:
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return 0
        return self.history_service.get_history_count()
    
    def get_decision_stats(self) -> dict:
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return {}
        return self.history_service.get_decision_stats()
    
    def clear_history(self) -> bool:
        if not self.history_service:
            logger.error("历史记录服务未初始化")
            return False
        return self.history_service.clear_history()
    
    # === 服务管理方法 ===
    def close(self):
        for key, svc in self.neo4j_services.items():
            try:
                svc.close()
            except Exception as e:
                logger.warning(f"关闭Neo4j服务失败[{key}]: {e}")
        logger.info("数据库连接已关闭")
    
    def init_databases(self):
        if self.history_service:
            self.history_service.init_database()
        for svc in self.neo4j_services.values():
            try:
                svc.init_database()
            except Exception:
                pass
    
    def is_ready(self) -> bool:
        return bool(self.neo4j_services) and self.history_service is not None

# 全局数据库管理器实例
db_manager = DatabaseManager()