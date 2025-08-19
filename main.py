"""
实体消歧服务主应用
"""
import logging
import sys
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config.settings import settings
from models import (
    AutoDecideRequest, 
    AutoDecideResponse, 
    MatchCandidatesRequest, 
    MatchCandidatesResponse,
    ErrorResponse
)
from services import db_manager, vectorization_service, disambiguation_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动实体消歧服务...")
    
    # 启动时初始化
    try:
        # 初始化数据库
        logger.info("📊 初始化数据库...")
        db_manager.init_databases()
        
        # 检查Nacos配置状态
        try:
            from services.nacos_config import nacos_config_service
            if nacos_config_service.is_available():
                logger.info("🔧 Nacos配置中心连接成功")
                neo4j_configs = nacos_config_service.parse_neo4j_datasources()
                logger.info(f"📋 从Nacos获取到 {len(neo4j_configs)} 个Neo4j数据源")
            else:
                logger.info("🔧 使用本地数据库配置")
        except Exception as e:
            logger.warning(f"⚠️ Nacos配置检查失败: {e}")
        
        # 加载向量化模型
        logger.info("🤖 加载向量化模型...")
        vectorization_service.load_bge_model()
        
        # 尝试加载现有索引
        logger.info("🔍 加载FAISS索引...")
        if not vectorization_service.load_index():
            logger.warning("⚠️ 索引不存在，启动后需要构建索引")
        
        # 加载消歧模型
        logger.info("🧠 加载消歧模型...")
        disambiguation_service.load_cross_encoder()
        
        logger.info("✅ 服务启动完成")
        
    except Exception as e:
        logger.error(f"❌ 服务启动失败: {e}")
        raise e
    
    yield
    
    # 关闭时清理
    logger.info("🛑 关闭实体消歧服务...")
    db_manager.close()

# 创建FastAPI应用
app = FastAPI(
    title="实体消歧服务",
    description="基于BGE-M3+CrossEncoder+RapidFuzz的实体消歧服务",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"全局异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "内部服务器错误", "detail": str(exc)}
    )

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "实体消歧服务",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查数据库连接
        dbs_info = db_manager.get_databases_info() if hasattr(db_manager, 'get_databases_info') else {"default": {"entity_count": db_manager.get_entity_count()}}
        
        # 检查向量化服务状态
        vectorization_stats = vectorization_service.get_all_index_stats() if hasattr(vectorization_service, 'get_all_index_stats') else vectorization_service.get_index_stats()
        
        # 检查消歧服务状态
        disambiguation_stats = disambiguation_service.get_disambiguation_stats()
        
        return {
            "status": "healthy",
            "databases": dbs_info,
            "vectorization": vectorization_service.get_all_index_stats() if hasattr(vectorization_service, 'get_all_index_stats') else vectorization_stats,
            "disambiguation": disambiguation_stats
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

@app.post("/auto-decide", response_model=AutoDecideResponse)
async def auto_decide(request: AutoDecideRequest):
    """自动决策实体消歧"""
    try:
        logger.info(f"收到自动决策请求: {request.entity.name}")
        
        # 验证数据库ID
        if request.database_key:
            if not db_manager.validate_database_key(request.database_key):
                available_keys = db_manager.get_available_database_keys()
                raise HTTPException(
                    status_code=400,
                    detail=f"数据库ID '{request.database_key}' 不存在。可用的数据库ID: {available_keys}"
                )
        
        # 执行自动决策
        result = disambiguation_service.auto_decide(
            request.entity,
            request.force_decision,
            db_key=request.database_key
        )
        
        logger.info(f"自动决策完成: {result.decision.value}")
        
        return AutoDecideResponse(
            result=result,
            message="自动决策完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"自动决策失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"自动决策失败: {str(e)}"
        )

@app.post("/match-candidates", response_model=MatchCandidatesResponse)
async def match_candidates(request: MatchCandidatesRequest):
    """获取匹配候选实体"""
    try:
        logger.info(f"收到候选匹配请求: {request.entity.name}")
        
        # 验证数据库ID
        if request.database_key:
            if not db_manager.validate_database_key(request.database_key):
                available_keys = db_manager.get_available_database_keys()
                raise HTTPException(
                    status_code=400,
                    detail=f"数据库ID '{request.database_key}' 不存在。可用的数据库ID: {available_keys}"
                )
        
        # 获取候选实体
        candidates = disambiguation_service.match_candidates(
            request.entity,
            request.top_k,
            db_key=request.database_key
        )
        
        logger.info(f"找到 {len(candidates)} 个候选实体")
        
        return MatchCandidatesResponse(
            candidates=candidates,
            total_count=len(candidates),
            message="候选匹配完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"候选匹配失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"候选匹配失败: {str(e)}"
        )

@app.get("/history")
async def get_disambiguation_history(limit: int = 100):
    """获取消歧历史"""
    try:
        histories = disambiguation_service.get_disambiguation_history(limit)
        return {
            "histories": histories,
            "total_count": len(histories),
            "message": "获取历史记录完成"
        }
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败: {str(e)}"
        )
 
@app.get("/databases")
async def list_databases():
    """列出可用Neo4j数据库及统计信息"""
    try:
        dbs = db_manager.list_databases() if hasattr(db_manager, 'list_databases') else ["default"]
        info = db_manager.get_databases_info() if hasattr(db_manager, 'get_databases_info') else {"default": {"entity_count": db_manager.get_entity_count()}}
        
        # 重新组织返回格式，让数据库ID和名称更清晰
        databases_list = []
        for db_id in dbs:
            if db_id in info:
                db_info = info[db_id]
                databases_list.append({
                    "id": db_id,  # 数据库ID，用于API操作
                    "name": db_info.get("name", f"Database {db_id}"),  # 数据库名称
                    "host": db_info.get("host", "Unknown"),  # 主机地址
                    "port": db_info.get("port", 0),  # 端口
                    "database": db_info.get("database", "neo4j"),  # 数据库名
                    "entity_count": db_info.get("entity_count", 0),  # 实体数量
                    "status": db_info.get("status", "unknown"),  # 连接状态
                    "remark": getattr(db_manager.get_service(db_id), 'remark', '') if db_manager.get_service(db_id) else ''  # 备注信息
                })
        
        default_key = db_manager.get_default_key() if hasattr(db_manager, 'get_default_key') else "default"
        
        return {
            "databases": databases_list,  # 数据库列表，包含详细信息
            "database_ids": dbs,  # 仅数据库ID列表，用于快速参考
            "default_key": default_key,  # 默认数据库ID
            "total_count": len(dbs),  # 数据库总数
            "message": f"成功获取 {len(dbs)} 个数据库信息"
        }
    except Exception as e:
        logger.error(f"获取数据库列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据库列表失败: {str(e)}")

@app.get("/stats")
async def get_stats():
    """获取服务统计信息"""
    try:
        # 数据库统计（多DB）
        databases_info = db_manager.get_databases_info() if hasattr(db_manager, 'get_databases_info') else {"default": {"entity_count": db_manager.get_entity_count()}}
        
        # 向量化统计（多DB）
        vectorization_stats = vectorization_service.get_all_index_stats() if hasattr(vectorization_service, 'get_all_index_stats') else vectorization_service.get_index_stats()
        
        # 消歧统计
        disambiguation_stats = disambiguation_service.get_disambiguation_stats()
        
        return {
            "databases": databases_info,
            "vectorization": vectorization_stats,
            "disambiguation": disambiguation_stats,
            "message": "统计信息获取完成"
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        )

@app.post("/rebuild-index")
async def rebuild_index(background_tasks: BackgroundTasks, database_key: str | None = None):
    """重建向量索引"""
    try:
        logger.info("开始重建向量索引")
        
        # 验证数据库ID
        if database_key:
            if not db_manager.validate_database_key(database_key):
                available_keys = db_manager.get_available_database_keys()
                raise HTTPException(
                    status_code=400,
                    detail=f"数据库ID '{database_key}' 不存在。可用的数据库ID: {available_keys}"
                )
        
        # 在后台任务中重建索引
        background_tasks.add_task(vectorization_service.rebuild_index, database_key)
        
        return {
            "message": "索引重建任务已启动，正在后台执行",
            "database_key": database_key or (db_manager.get_default_key() if hasattr(db_manager, 'get_default_key') else 'default')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重建索引失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"重建索引失败: {str(e)}"
        )

@app.post("/refresh-config")
async def refresh_nacos_config():
    """刷新Nacos配置"""
    try:
        logger.info("收到刷新Nacos配置请求")
        
        success = db_manager.refresh_nacos_config()
        
        if success:
            return {
                "message": "Nacos配置刷新成功",
                "databases": db_manager.list_databases() if hasattr(db_manager, 'list_databases') else ["default"],
                "default_key": db_manager.get_default_key() if hasattr(db_manager, 'get_default_key') else "default"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Nacos配置刷新失败"
            )
        
    except Exception as e:
        logger.error(f"刷新Nacos配置失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"刷新Nacos配置失败: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 启动服务器: {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    ) 