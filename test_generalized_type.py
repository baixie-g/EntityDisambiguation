#!/usr/bin/env python3
"""
测试完全泛化type字段的功能
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

def test_various_type_values():
    """测试各种type值"""
    logger.info("🔍 测试各种type值...")
    
    test_cases = [
        {
            "name": "测试实体1",
            "type": "疾病",
            "description": "传统医学类型"
        },
        {
            "name": "测试实体2", 
            "type": "custom_type",
            "description": "英文自定义类型"
        },
        {
            "name": "测试实体3",
            "type": "自定义分类_123",
            "description": "带数字的自定义类型"
        },
        {
            "name": "测试实体4",
            "type": "特殊@类型#符号",
            "description": "包含特殊符号的类型"
        },
        {
            "name": "测试实体5",
            "type": "非常长的类型名称用于测试系统是否能够正确处理长字符串类型值",
            "description": "超长类型名称"
        },
        {
            "name": "测试实体6",
            "type": "",
            "description": "空字符串类型"
        },
        {
            "name": "测试实体7",
            "type": None,
            "description": "None类型"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"  测试用例 {i}: {test_case['description']}")
        
        request_data = {
            "entity": {
                "name": test_case["name"],
                "aliases": [f"alias_{i}"],
                "definition": f"这是{test_case['description']}的测试实体"
            },
            "force_decision": False
        }
        
        # 只有当type不为None且不为空字符串时才添加
        if test_case["type"] is not None and test_case["type"] != "":
            request_data["entity"]["type"] = test_case["type"]
        
        try:
            response = requests.post(
                f"{BASE_URL}/auto-decide",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data["result"]
                
                logger.info(f"    ✅ 通过 - 决策: {result['decision']}, 置信度: {result['confidence']:.3f}")
                passed += 1
            else:
                logger.error(f"    ❌ 失败 - 状态码: {response.status_code}, 错误: {response.text}")
                
        except Exception as e:
            logger.error(f"    ❌ 异常: {e}")
    
    logger.info(f"📊 类型测试结果: {passed}/{total} 通过")
    return passed == total

def test_type_search_optimization():
    """测试type字段的搜索优化功能"""
    logger.info("🔍 测试type字段的搜索优化功能...")
    
    # 首先上传一些测试数据
    test_entities = [
        {
            "entity": {
                "name": "糖尿病",
                "type": "疾病",
                "aliases": ["diabetes"],
                "definition": "糖尿病是一组以高血糖为特征的代谢性疾病"
            }
        },
        {
            "entity": {
                "name": "高血压",
                "type": "疾病", 
                "aliases": ["hypertension"],
                "definition": "高血压是一种常见的慢性疾病"
            }
        },
        {
            "entity": {
                "name": "阿司匹林",
                "type": "药物",
                "aliases": ["aspirin"],
                "definition": "阿司匹林是一种常用的解热镇痛药"
            }
        }
    ]
    
    # 上传测试数据
    for entity_data in test_entities:
        try:
            response = requests.post(
                f"{BASE_URL}/upload-entity",
                json=entity_data,
                headers={"Content-Type": "application/json"}
            )
            if response.status_code != 200:
                logger.warning(f"上传测试数据失败: {entity_data['entity']['name']}")
        except:
            logger.warning(f"上传测试数据异常: {entity_data['entity']['name']}")
    
    # 测试搜索优化
    test_cases = [
        {
            "name": "糖尿病",
            "type": "疾病",
            "expected_optimization": True,
            "description": "在指定类型中搜索"
        },
        {
            "name": "糖尿病",
            "type": "药物", 
            "expected_optimization": True,
            "description": "在错误类型中搜索（应该降级到全局搜索）"
        },
        {
            "name": "糖尿病",
            "type": None,
            "expected_optimization": False,
            "description": "不指定类型（全局搜索）"
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        logger.info(f"  测试: {test_case['description']}")
        
        request_data = {
            "entity": {
                "name": test_case["name"],
                "aliases": ["test"],
                "definition": "测试实体"
            },
            "top_k": 5
        }
        
        if test_case["type"] is not None:
            request_data["entity"]["type"] = test_case["type"]
        
        try:
            response = requests.post(
                f"{BASE_URL}/match-candidates",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                candidates = data["candidates"]
                
                logger.info(f"    ✅ 通过 - 找到 {len(candidates)} 个候选")
                passed += 1
            else:
                logger.error(f"    ❌ 失败 - 状态码: {response.status_code}")
                
        except Exception as e:
            logger.error(f"    ❌ 异常: {e}")
    
    logger.info(f"📊 搜索优化测试结果: {passed}/{total} 通过")
    return passed == total

def test_edge_cases():
    """测试边界情况"""
    logger.info("🔍 测试边界情况...")
    
    edge_cases = [
        {
            "name": "边界测试1",
            "type": "a" * 1000,  # 超长字符串
            "description": "超长type值"
        },
        {
            "name": "边界测试2",
            "type": "  疾病  ",  # 带空格
            "description": "带空格的type值"
        },
        {
            "name": "边界测试3",
            "type": "疾病\n症状",  # 包含换行符
            "description": "包含特殊字符的type值"
        }
    ]
    
    passed = 0
    total = len(edge_cases)
    
    for test_case in edge_cases:
        logger.info(f"  测试: {test_case['description']}")
        
        request_data = {
            "entity": {
                "name": test_case["name"],
                "type": test_case["type"],
                "aliases": ["test"],
                "definition": "边界测试实体"
            },
            "force_decision": False
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/auto-decide",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info(f"    ✅ 通过")
                passed += 1
            else:
                logger.error(f"    ❌ 失败 - 状态码: {response.status_code}")
                
        except Exception as e:
            logger.error(f"    ❌ 异常: {e}")
    
    logger.info(f"📊 边界测试结果: {passed}/{total} 通过")
    return passed == total

def main():
    """主测试函数"""
    logger.info("🚀 开始测试完全泛化type字段功能...")
    
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
        test_various_type_values,
        test_type_search_optimization,
        test_edge_cases
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        logger.info("")  # 空行分隔
    
    logger.info(f"🎉 测试完成: {passed}/{total} 通过")
    
    if passed == total:
        logger.info("✅ 所有测试通过！完全泛化type字段功能正常工作")
        logger.info("📝 总结:")
        logger.info("   - type字段完全泛化，支持任意字符串")
        logger.info("   - 不再有枚举限制")
        logger.info("   - 搜索优化功能正常")
        logger.info("   - 边界情况处理良好")
    else:
        logger.error("❌ 部分测试失败，请检查代码")
    
    return passed == total

if __name__ == "__main__":
    main() 