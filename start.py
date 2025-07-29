#!/usr/bin/env python3
"""
启动脚本 - 完整的项目启动流程
"""
import os
import sys
import time
import logging
import subprocess
import signal
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """检查依赖包是否安装"""
    logger.info("🔍 检查依赖包...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "sentence-transformers",
        "faiss-cpu",
        "rapidfuzz",
        "numpy",
        "torch",
        "transformers",
        "FlagEmbedding",
        "python-Levenshtein"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        logger.info("请运行: pip install -r requirements.txt")
        return True
    
    logger.info("✅ 所有依赖包都已安装")
    return True

def check_data_directory():
    """检查数据目录是否存在"""
    logger.info("🔍 检查数据目录...")
    
    data_dir = Path("data")
    if not data_dir.exists():
        logger.info("创建数据目录...")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查示例数据文件
    sample_file = data_dir / "sample_entities.json"
    if not sample_file.exists():
        logger.error(f"❌ 示例数据文件不存在: {sample_file}")
        return False
    
    logger.info("✅ 数据目录检查通过")
    return True

def initialize_data():
    """初始化数据"""
    logger.info("🔄 初始化数据...")
    
    try:
        # 运行初始化脚本
        result = subprocess.run(
            [sys.executable, "init_data.py"],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            logger.info("✅ 数据初始化成功")
            return True
        else:
            logger.error(f"❌ 数据初始化失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ 数据初始化超时")
        return False
    except Exception as e:
        logger.error(f"❌ 数据初始化异常: {e}")
        return False

def start_server():
    """启动服务器"""
    logger.info("🚀 启动服务器...")
    
    try:
        # 启动FastAPI服务器
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务器启动
        time.sleep(5)
        
        # 检查进程是否还在运行
        if process.poll() is None:
            logger.info("✅ 服务器启动成功")
            logger.info("📡 服务地址: http://localhost:8000")
            logger.info("📖 API文档: http://localhost:8000/docs")
            return process
        else:
            stdout, stderr = process.communicate()
            logger.error(f"❌ 服务器启动失败")
            logger.error(f"   标准输出: {stdout}")
            logger.error(f"   错误输出: {stderr}")
            return None
            
    except Exception as e:
        logger.error(f"❌ 启动服务器异常: {e}")
        return None

def test_api():
    """测试API"""
    logger.info("🧪 测试API...")
    
    try:
        # 运行API测试
        result = subprocess.run(
            [sys.executable, "test_api.py"],
            capture_output=True,
            text=True,
            timeout=60  # 1分钟超时
        )
        
        if result.returncode == 0:
            logger.info("✅ API测试通过")
            return True
        else:
            logger.error(f"❌ API测试失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ API测试超时")
        return False
    except Exception as e:
        logger.error(f"❌ API测试异常: {e}")
        return False

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info("🛑 收到停止信号，正在关闭服务...")
    sys.exit(0)

def main():
    """主函数"""
    logger.info("🚀 开始启动实体消歧服务...")
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 步骤1: 检查依赖包
    if not check_dependencies():
        sys.exit(1)
    
    # 步骤2: 检查数据目录
    if not check_data_directory():
        sys.exit(1)
    
    # 步骤3: 初始化数据
    if not initialize_data():
        logger.error("❌ 初始化失败，请检查错误信息")
        sys.exit(1)
    
    # 步骤4: 启动服务器
    server_process = start_server()
    if server_process is None:
        sys.exit(1)
    
    # 步骤5: 测试API
    time.sleep(3)  # 等待服务器完全启动
    if not test_api():
        logger.warning("⚠️ API测试失败，但服务器仍在运行")
    
    logger.info("🎉 实体消歧服务启动完成！")
    logger.info("=" * 60)
    logger.info("📡 服务地址: http://localhost:8000")
    logger.info("📖 API文档: http://localhost:8000/docs")
    logger.info("🔍 健康检查: http://localhost:8000/health")
    logger.info("📊 统计信息: http://localhost:8000/stats")
    logger.info("=" * 60)
    logger.info("按 Ctrl+C 停止服务")
    
    try:
        # 等待进程结束
        server_process.wait()
    except KeyboardInterrupt:
        logger.info("🛑 收到停止信号")
    finally:
        # 清理进程
        try:
            server_process.terminate()
            server_process.wait(timeout=10)
        except:
            server_process.kill()
        logger.info("✅ 服务已停止")

if __name__ == "__main__":
    main() 