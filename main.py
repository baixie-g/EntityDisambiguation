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
        entity_count = db_manager.get_entity_count()
        
        # 检查向量化服务状态
        vectorization_stats = vectorization_service.get_index_stats()
        
        # 检查消歧服务状态
        disambiguation_stats = disambiguation_service.get_disambiguation_stats()
        
        return {
            "status": "healthy",
            "database": {
                "connected": True,
                "entity_count": entity_count
            },
            "vectorization": vectorization_stats,
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
        
        # 执行自动决策
        result = disambiguation_service.auto_decide(
            request.entity, 
            request.force_decision
        )
        
        logger.info(f"自动决策完成: {result.decision.value}")
        
        return AutoDecideResponse(
            result=result,
            message="自动决策完成"
        )
        
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
        
        # 获取候选实体
        candidates = disambiguation_service.match_candidates(
            request.entity,
            request.top_k
        )
        
        logger.info(f"找到 {len(candidates)} 个候选实体")
        
        return MatchCandidatesResponse(
            candidates=candidates,
            total_count=len(candidates),
            message="候选匹配完成"
        )
        
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

@app.get("/stats")
async def get_stats():
    """获取服务统计信息"""
    try:
        # 数据库统计
        entity_count = db_manager.get_entity_count()
        
        # 向量化统计
        vectorization_stats = vectorization_service.get_index_stats()
        
        # 消歧统计
        disambiguation_stats = disambiguation_service.get_disambiguation_stats()
        
        return {
            "database": {
                "entity_count": entity_count
            },
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
async def rebuild_index(background_tasks: BackgroundTasks):
    """重建向量索引"""
    try:
        logger.info("开始重建向量索引")
        
        # 在后台任务中重建索引
        background_tasks.add_task(vectorization_service.rebuild_index)
        
        return {
            "message": "索引重建任务已启动，正在后台执行"
        }
        
    except Exception as e:
        logger.error(f"重建索引失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"重建索引失败: {str(e)}"
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