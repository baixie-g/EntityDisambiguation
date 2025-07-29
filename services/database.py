"""
SQLite数据库服务 - 专门用于消歧历史记录存储
"""
import sqlite3
import json
import logging
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from models import DisambiguationHistory, EntityScore, DecisionType, Entity
from config.settings import settings

logger = logging.getLogger(__name__)

class HistoryDatabaseService:
    """SQLite历史记录数据库服务类"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.SQLITE_DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """初始化历史记录数据库"""
        # 确保数据目录存在
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建消歧历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS disambiguation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    input_entity TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    match_id TEXT,
                    match_entity TEXT,
                    scores TEXT NOT NULL,
                    reasoning TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON disambiguation_history(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_decision ON disambiguation_history(decision)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_match_id ON disambiguation_history(match_id)")
            
            conn.commit()
            logger.info(f"历史记录数据库初始化完成: {self.db_path}")
    
    def save_disambiguation_history(self, history: DisambiguationHistory) -> bool:
        """保存消歧历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO disambiguation_history 
                    (input_entity, decision, match_id, match_entity, scores, reasoning, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    history.input_entity.model_dump_json(),
                    history.decision.value,
                    history.match_id,
                    history.match_entity.model_dump_json() if history.match_entity else None,
                    history.scores.model_dump_json(),
                    history.reasoning,
                    history.timestamp.isoformat()
                ))
                
                conn.commit()
                logger.info("消歧历史保存成功")
                return True
                
        except Exception as e:
            logger.error(f"保存消歧历史失败: {e}")
            return False
    
    def get_disambiguation_history(self, limit: int = 100) -> List[DisambiguationHistory]:
        """获取消歧历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM disambiguation_history 
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                histories = []
                
                for row in rows:
                    try:
                        history = DisambiguationHistory(
                            input_entity=Entity.model_validate_json(row[1]),
                            decision=DecisionType(row[2]),
                            match_id=row[3],
                            match_entity=Entity.model_validate_json(row[4]) if row[4] else None,
                            scores=EntityScore.model_validate_json(row[5]),
                            reasoning=row[6] or "",
                            timestamp=datetime.fromisoformat(row[7])
                        )
                        histories.append(history)
                    except Exception as e:
                        logger.error(f"解析历史记录失败: {e}")
                        continue
                
                return histories
                
        except Exception as e:
            logger.error(f"获取消歧历史失败: {e}")
            return []
    
    def get_history_count(self) -> int:
        """获取历史记录数量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM disambiguation_history")
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"获取历史记录数量失败: {e}")
            return 0
    
    def get_decision_stats(self) -> dict:
        """获取决策统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT decision, COUNT(*) 
                    FROM disambiguation_history 
                    GROUP BY decision
                """)
                
                stats = {}
                for row in cursor.fetchall():
                    stats[row[0]] = row[1]
                
                return stats
                
        except Exception as e:
            logger.error(f"获取决策统计失败: {e}")
            return {}
    
    def clear_history(self) -> bool:
        """清空历史记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM disambiguation_history")
                conn.commit()
                logger.info("历史记录已清空")
                return True
        except Exception as e:
            logger.error(f"清空历史记录失败: {e}")
            return False

# 全局历史记录数据库实例
history_db_service = HistoryDatabaseService() 