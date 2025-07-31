#!/usr/bin/env python3
"""
测试可选type字段的功能
"""
import requests
import json
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8002"

def test_with_type():
    """测试提供type字段的情况"""
    logger.info("🔍 测试提供type字段的情况...")
    
    test_case = {
        "entity": {
            "name": "糖尿病",
            "type": "疾病",
            "aliases": ["diabetes"],
            "definition": "糖尿病是一组以高血糖为特征的代谢性疾病"
        },
        "force_decision": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auto-decide",
            json=test_case,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data["result"]
            
            logger.info(f"✅ 提供type字段测试通过:")
            logger.info(f"   决策: {result['decision']}")
            logger.info(f"   置信度: {result['confidence']:.3f}")
            logger.info(f"   推理: {result['reasoning']}")
            return True
        else:
            logger.error(f"❌ 提供type字段测试失败: {response.status_code}")
            logger.error(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 提供type字段测试异常: {e}")
        return False

def test_without_type():
    """测试不提供type字段的情况"""
    logger.info("🔍 测试不提供type字段的情况...")
    
    test_case = {
        "entity": {
            "name": "糖尿病",
            "aliases": ["diabetes"],
            "definition": "糖尿病是一组以高血糖为特征的代谢性疾病"
        },
        "force_decision": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auto-decide",
            json=test_case,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data["result"]
            
            logger.info(f"✅ 不提供type字段测试通过:")
            logger.info(f"   决策: {result['decision']}")
            logger.info(f"   置信度: {result['confidence']:.3f}")
            logger.info(f"   推理: {result['reasoning']}")
            return True
        else:
            logger.error(f"❌ 不提供type字段测试失败: {response.status_code}")
            logger.error(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 不提供type字段测试异常: {e}")
        return False

def test_custom_type():
    """测试自定义type字段的情况"""
    logger.info("🔍 测试自定义type字段的情况...")
    
    test_case = {
        "entity": {
            "name": "自定义实体",
            "type": "自定义类型",
            "aliases": ["custom"],
            "definition": "这是一个自定义类型的实体"
        },
        "force_decision": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auto-decide",
            json=test_case,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data["result"]
            
            logger.info(f"✅ 自定义type字段测试通过:")
            logger.info(f"   决策: {result['decision']}")
            logger.info(f"   置信度: {result['confidence']:.3f}")
            logger.info(f"   推理: {result['reasoning']}")
            return True
        else:
            logger.error(f"❌ 自定义type字段测试失败: {response.status_code}")
            logger.error(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 自定义type字段测试异常: {e}")
        return False

def test_match_candidates_without_type():
    """测试match-candidates接口不提供type字段的情况"""
    logger.info("🔍 测试match-candidates接口不提供type字段的情况...")
    
    test_case = {
        "entity": {
            "name": "DM",
            "aliases": ["糖尿"],
            "definition": "一种代谢性疾病"
        },
        "top_k": 3
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/match-candidates",
            json=test_case,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            candidates = data["candidates"]
            
            logger.info(f"✅ match-candidates不提供type字段测试通过:")
            logger.info(f"   找到 {len(candidates)} 个候选实体")
            
            for i, candidate in enumerate(candidates[:2], 1):
                logger.info(f"   候选{i}: {candidate['entity']['name']}")
                logger.info(f"      排名: {candidate['rank']}")
                logger.info(f"      最终得分: {candidate['score']['final_score']:.3f}")
            
            return True
        else:
            logger.error(f"❌ match-candidates不提供type字段测试失败: {response.status_code}")
            logger.error(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ match-candidates不提供type字段测试异常: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🚀 开始测试可选type字段功能...")
    
    # 测试健康检查
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            logger.error("❌ 服务未启动，请先启动服务")
            return False
    except Exception as e:
        logger.error(f"❌ 无法连接到服务: {e}")
        return False
    
    # 运行测试
    tests = [
        test_with_type,
        test_without_type,
        test_custom_type,
        test_match_candidates_without_type
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        logger.info("")  # 空行分隔
    
    logger.info(f"🎉 测试完成: {passed}/{total} 通过")
    
    if passed == total:
        logger.info("✅ 所有测试通过！可选type字段功能正常工作")
    else:
        logger.error("❌ 部分测试失败，请检查代码")
    
    return passed == total

if __name__ == "__main__":
    main() 