"""
服务模块初始化
"""
from .database_factory import db_manager
from .vectorization import vectorization_service
from .disambiguation import disambiguation_service

__all__ = [
    "db_manager",
    "vectorization_service", 
    "disambiguation_service"
] 