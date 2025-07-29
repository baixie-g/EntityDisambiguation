"""
Neo4j数据库服务 - 管理实体和历史记录
"""
import logging
import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from models import Entity, DisambiguationHistory, EntityScore, DecisionType
from config.settings import settings

logger = logging.getLogger(__name__)

# 尝试导入Neo4j驱动
try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, AuthError
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    logger.warning("Neo4j驱动未安装，请运行: pip install neo4j")

class Neo4jDatabaseService:
    """Neo4j数据库服务类"""
    
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        if not NEO4J_AVAILABLE:
            raise ImportError("Neo4j驱动未安装，请运行: pip install neo4j")
            
        self.uri = uri or settings.NEO4J_URI
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self.driver = None
        self.connect()
    
    def connect(self):
        """连接Neo4j数据库"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Neo4j连接成功: {self.uri}")
            self.init_database()
        except ServiceUnavailable as e:
            logger.error(f"Neo4j服务不可用: {e}")
            raise e
        except AuthError as e:
            logger.error(f"Neo4j认证失败: {e}")
            raise e
        except Exception as e:
            logger.error(f"Neo4j连接失败: {e}")
            raise e
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j连接已关闭")
    
    def init_database(self):
        """初始化数据库约束和索引"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return
            
        with self.driver.session() as session:
            # 创建实体节点的唯一约束
            session.run("""
                CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.id IS UNIQUE
            """)
            
            # 创建实体名称索引
            session.run("""
                CREATE INDEX entity_name_index IF NOT EXISTS
                FOR (e:Entity) ON (e.name)
            """)
            
            # 创建实体类型索引
            session.run("""
                CREATE INDEX entity_type_index IF NOT EXISTS
                FOR (e:Entity) ON (e.type)
            """)
            
            # 创建消歧历史节点的索引
            session.run("""
                CREATE INDEX disambiguation_timestamp_index IF NOT EXISTS
                FOR (h:DisambiguationHistory) ON (h.timestamp)
            """)
            
            logger.info("Neo4j数据库初始化完成")
    
    def save_entity(self, entity: Entity) -> bool:
        """保存实体到Neo4j"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return False
            
        try:
            with self.driver.session() as session:
                # 如果没有ID，生成一个
                if not entity.id:
                    entity.id = self._generate_entity_id(entity.type.value, entity.name)
                
                # 构建Cypher查询
                query = """
                MERGE (e:Entity {id: $id})
                SET e.name = $name,
                    e.type = $type,
                    e.aliases = $aliases,
                    e.definition = $definition,
                    e.attributes = $attributes,
                    e.source = $source,
                    e.create_time = $create_time,
                    e.updated_time = datetime()
                RETURN e
                """
                
                result = session.run(query, {
                    'id': entity.id,
                    'name': entity.name,
                    'type': entity.type.value,
                    'aliases': entity.aliases,
                    'definition': entity.definition,
                    'attributes': json.dumps(entity.attributes, ensure_ascii=False),
                    'source': entity.source,
                    'create_time': entity.create_time.isoformat() if entity.create_time else datetime.now().isoformat()
                })
                
                if result.single():
                    logger.info(f"实体保存成功: {entity.id}")
                    return True
                else:
                    logger.error(f"实体保存失败: {entity.id}")
                    return False
                    
        except Exception as e:
            logger.error(f"保存实体失败: {e}")
            return False
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """根据ID获取实体"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return None
            
        try:
            with self.driver.session() as session:
                query = """
                MATCH (e:Entity {id: $id})
                RETURN e
                """
                
                result = session.run(query, {'id': entity_id})
                record = result.single()
                
                if record:
                    return self._record_to_entity(record['e'])
                return None
                
        except Exception as e:
            logger.error(f"获取实体失败: {e}")
            return None
    
    def get_all_entities(self) -> List[Entity]:
        """获取所有实体"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return []
            
        try:
            with self.driver.session() as session:
                query = """
                MATCH (e:Entity)
                RETURN e
                ORDER BY e.create_time DESC
                """
                
                result = session.run(query)
                entities = []
                
                for record in result:
                    entity = self._record_to_entity(record['e'])
                    if entity:
                        entities.append(entity)
                
                return entities
                
        except Exception as e:
            logger.error(f"获取所有实体失败: {e}")
            return []
    
    def search_entities(self, query: str, entity_type: Optional[str] = None, limit: int = 100) -> List[Entity]:
        """搜索实体"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return []
            
        try:
            with self.driver.session() as session:
                if entity_type:
                    cypher_query = """
                    MATCH (e:Entity)
                    WHERE e.type = $entity_type AND 
                          (e.name CONTAINS $query OR 
                           any(alias IN e.aliases WHERE alias CONTAINS $query))
                    RETURN e
                    ORDER BY e.name
                    LIMIT $limit
                    """
                    params = {'query': query, 'entity_type': entity_type, 'limit': limit}
                else:
                    cypher_query = """
                    MATCH (e:Entity)
                    WHERE e.name CONTAINS $query OR 
                          any(alias IN e.aliases WHERE alias CONTAINS $query)
                    RETURN e
                    ORDER BY e.name
                    LIMIT $limit
                    """
                    params = {'query': query, 'limit': limit}
                
                result = session.run(cypher_query, params)
                entities = []
                
                for record in result:
                    entity = self._record_to_entity(record['e'])
                    if entity:
                        entities.append(entity)
                
                return entities
                
        except Exception as e:
            logger.error(f"搜索实体失败: {e}")
            return []
    
    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """根据类型获取实体"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return []
            
        try:
            with self.driver.session() as session:
                query = """
                MATCH (e:Entity {type: $type})
                RETURN e
                ORDER BY e.name
                """
                
                result = session.run(query, {'type': entity_type})
                entities = []
                
                for record in result:
                    entity = self._record_to_entity(record['e'])
                    if entity:
                        entities.append(entity)
                
                return entities
                
        except Exception as e:
            logger.error(f"根据类型获取实体失败: {e}")
            return []
    
    def save_disambiguation_history(self, history: DisambiguationHistory) -> bool:
        """保存消歧历史"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return False
            
        try:
            with self.driver.session() as session:
                query = """
                CREATE (h:DisambiguationHistory {
                    input_entity: $input_entity,
                    decision: $decision,
                    match_id: $match_id,
                    match_entity: $match_entity,
                    scores: $scores,
                    reasoning: $reasoning,
                    timestamp: $timestamp
                })
                RETURN h
                """
                
                result = session.run(query, {
                    'input_entity': history.input_entity.model_dump_json(),
                    'decision': history.decision.value,
                    'match_id': history.match_id,
                    'match_entity': history.match_entity.model_dump_json() if history.match_entity else None,
                    'scores': history.scores.model_dump_json(),
                    'reasoning': history.reasoning,
                    'timestamp': history.timestamp.isoformat()
                })
                
                if result.single():
                    logger.info("消歧历史保存成功")
                    return True
                else:
                    logger.error("消歧历史保存失败")
                    return False
                    
        except Exception as e:
            logger.error(f"保存消歧历史失败: {e}")
            return False
    
    def get_disambiguation_history(self, limit: int = 100) -> List[DisambiguationHistory]:
        """获取消歧历史"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return []
            
        try:
            with self.driver.session() as session:
                query = """
                MATCH (h:DisambiguationHistory)
                RETURN h
                ORDER BY h.timestamp DESC
                LIMIT $limit
                """
                
                result = session.run(query, {'limit': limit})
                histories = []
                
                for record in result:
                    try:
                        h = record['h']
                        history = DisambiguationHistory(
                            input_entity=Entity.model_validate_json(h['input_entity']),
                            decision=DecisionType(h['decision']),
                            match_id=h['match_id'],
                            match_entity=Entity.model_validate_json(h['match_entity']) if h['match_entity'] else None,
                            scores=EntityScore.model_validate_json(h['scores']),
                            reasoning=h['reasoning'] or "",
                            timestamp=datetime.fromisoformat(h['timestamp'])
                        )
                        histories.append(history)
                    except Exception as e:
                        logger.error(f"解析历史记录失败: {e}")
                        continue
                
                return histories
                
        except Exception as e:
            logger.error(f"获取消歧历史失败: {e}")
            return []
    
    def get_entity_count(self) -> int:
        """获取实体数量"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return 0
            
        try:
            with self.driver.session() as session:
                query = "MATCH (e:Entity) RETURN count(e) as count"
                result = session.run(query)
                record = result.single()
                return record['count'] if record else 0
        except Exception as e:
            logger.error(f"获取实体数量失败: {e}")
            return 0
    
    def create_entity_relationship(self, entity1_id: str, entity2_id: str, relationship_type: str, properties: Optional[Dict[str, Any]] = None) -> bool:
        """创建实体间关系"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return False
            
        try:
            with self.driver.session() as session:
                # 使用参数化查询避免类型错误
                query = """
                MATCH (e1:Entity {id: $entity1_id}), (e2:Entity {id: $entity2_id})
                CREATE (e1)-[r:RELATIONSHIP]->(e2)
                SET r.type = $relationship_type
                SET r += $properties
                RETURN r
                """
                
                result = session.run(query, {
                    'entity1_id': entity1_id,
                    'entity2_id': entity2_id,
                    'relationship_type': relationship_type,
                    'properties': properties or {}
                })
                
                if result.single():
                    logger.info(f"关系创建成功: {entity1_id} -> {entity2_id}")
                    return True
                else:
                    logger.error(f"关系创建失败: {entity1_id} -> {entity2_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"创建实体关系失败: {e}")
            return False
    
    def get_related_entities(self, entity_id: str, relationship_type: Optional[str] = None) -> List[Entity]:
        """获取相关实体"""
        if not self.driver:
            logger.error("Neo4j驱动未初始化")
            return []
            
        try:
            with self.driver.session() as session:
                if relationship_type:
                    query = """
                    MATCH (e1:Entity {id: $entity_id})-[r:RELATIONSHIP]->(e2:Entity)
                    WHERE r.type = $relationship_type
                    RETURN e2
                    """
                    params = {'entity_id': entity_id, 'relationship_type': relationship_type}
                else:
                    query = """
                    MATCH (e1:Entity {id: $entity_id})-[r:RELATIONSHIP]->(e2:Entity)
                    RETURN e2
                    """
                    params = {'entity_id': entity_id}
                
                result = session.run(query, params)
                entities = []
                
                for record in result:
                    entity = self._record_to_entity(record['e2'])
                    if entity:
                        entities.append(entity)
                
                return entities
                
        except Exception as e:
            logger.error(f"获取相关实体失败: {e}")
            return []
    
    def _generate_entity_id(self, entity_type: str, name: str) -> str:
        """生成实体ID"""
        type_prefix = {
            "疾病": "disease",
            "症状": "symptom",
            "药物": "drug",
            "治疗": "treatment",
            "基因": "gene",
            "蛋白质": "protein",
            "器官": "organ",
            "其他": "other"
        }.get(entity_type, "entity")
        
        # 简单的ID生成策略
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{type_prefix}_{timestamp}_{abs(hash(name)) % 10000:04d}"
    
    def _record_to_entity(self, record) -> Optional[Entity]:
        """将Neo4j记录转换为实体对象"""
        try:
            return Entity(
                id=record.get('id'),
                name=record.get('name'),
                type=record.get('type'),
                aliases=record.get('aliases', []),
                definition=record.get('definition'),
                attributes=json.loads(record.get('attributes', '{}')) if record.get('attributes') else {},
                source=record.get('source'),
                create_time=datetime.fromisoformat(record.get('create_time')) if record.get('create_time') else None
            )
        except Exception as e:
            logger.error(f"转换实体记录失败: {e}")
            return None

# 创建Neo4j数据库实例的函数
def create_neo4j_db_service() -> Optional[Neo4jDatabaseService]:
    """创建Neo4j数据库服务实例"""
    try:
        return Neo4jDatabaseService()
    except Exception as e:
        logger.error(f"创建Neo4j数据库服务失败: {e}")
        return None 