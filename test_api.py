#!/usr/bin/env python3
"""
API测试脚本 - 验证实体消歧服务接口
"""
import requests
import json
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查接口"""
    logger.info("🔍 测试健康检查接口...")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ 健康检查通过: {data['status']}")
            logger.info(f"📊 实体数量: {data['database']['entity_count']}")
            logger.info(f"🤖 模型状态: {data['vectorization']['model_loaded']}")
            logger.info(f"🔍 索引状态: {data['vectorization']['index_loaded']}")
            return True
        else:
            logger.error(f"❌ 健康检查失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 健康检查异常: {e}")
        return False

def test_auto_decide():
    """测试自动决策接口"""
    logger.info("🔍 测试自动决策接口...")
    
    # 测试用例1: 完全匹配的实体
    test_case_1 = {
        "entity": {
            "name": "糖尿病",
            "type": "疾病",
            "aliases": ["diabetes", "糖尿"],
            "definition": "糖尿病是一组以高血糖为特征的代谢性疾病",
            "attributes": {
                "症状": ["多尿", "口渴", "体重下降"],
                "治疗方法": ["饮食控制", "胰岛素治疗"]
            },
            "source": "测试数据"
        },
        "force_decision": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auto-decide",
            json=test_case_1,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data["result"]
            
            logger.info(f"✅ 测试用例1通过:")
            logger.info(f"   决策: {result['decision']}")
            logger.info(f"   置信度: {result['confidence']:.3f}")
            logger.info(f"   推理: {result['reasoning']}")
            
            if result["decision"] == "merge":
                logger.info(f"   匹配实体: {result['match_entity']['name']}")
                logger.info(f"   BGE得分: {result['scores']['bge_score']:.3f}")
                logger.info(f"   最终得分: {result['scores']['final_score']:.3f}")
        else:
            logger.error(f"❌ 测试用例1失败: {response.status_code}")
            logger.error(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试用例1异常: {e}")
        return False
    
    # 测试用例2: 新实体
    test_case_2 = {
        "entity": {
            "name": "新冠肺炎",
            "type": "疾病",
            "aliases": ["COVID-19", "新型冠状病毒肺炎"],
            "definition": "由新型冠状病毒引起的急性呼吸道传染病",
            "attributes": {
                "症状": ["发热", "咳嗽", "乏力"],
                "传播方式": ["飞沫传播", "接触传播"]
            },
            "source": "测试数据"
        },
        "force_decision": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/auto-decide",
            json=test_case_2,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            result = data["result"]
            
            logger.info(f"✅ 测试用例2通过:")
            logger.info(f"   决策: {result['decision']}")
            logger.info(f"   置信度: {result['confidence']:.3f}")
            logger.info(f"   推理: {result['reasoning']}")
        else:
            logger.error(f"❌ 测试用例2失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试用例2异常: {e}")
        return False
    
    return True

def test_match_candidates():
    """测试候选匹配接口"""
    logger.info("🔍 测试候选匹配接口...")
    
    test_request = {
        "entity": {
            "name": "DM",
            "type": "疾病",
            "aliases": ["糖尿"],
            "definition": "一种代谢性疾病",
            "source": "测试数据"
        },
        "top_k": 3,
        "include_scores": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/match-candidates",
            json=test_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            candidates = data["candidates"]
            
            logger.info(f"✅ 候选匹配测试通过:")
            logger.info(f"   找到 {len(candidates)} 个候选实体")
            
            for i, candidate in enumerate(candidates, 1):
                logger.info(f"   候选{i}: {candidate['entity']['name']}")
                logger.info(f"      排名: {candidate['rank']}")
                logger.info(f"      最终得分: {candidate['score']['final_score']:.3f}")
                logger.info(f"      详情: {candidate['similarity_details']}")
                
            return True
        else:
            logger.error(f"❌ 候选匹配测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 候选匹配测试异常: {e}")
        return False

def test_stats():
    """测试统计信息接口"""
    logger.info("🔍 测试统计信息接口...")
    
    try:
        response = requests.get(f"{BASE_URL}/stats")
        
        if response.status_code == 200:
            data = response.json()
            
            logger.info(f"✅ 统计信息测试通过:")
            logger.info(f"   数据库实体数: {data['database']['entity_count']}")
            logger.info(f"   向量化状态: {data['vectorization']}")
            logger.info(f"   消歧统计: {data['disambiguation']}")
            
            return True
        else:
            logger.error(f"❌ 统计信息测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 统计信息测试异常: {e}")
        return False

def test_history():
    """测试历史记录接口"""
    logger.info("🔍 测试历史记录接口...")
    
    try:
        response = requests.get(f"{BASE_URL}/history?limit=5")
        
        if response.status_code == 200:
            data = response.json()
            histories = data["histories"]
            
            logger.info(f"✅ 历史记录测试通过:")
            logger.info(f"   历史记录数: {len(histories)}")
            
            for i, history in enumerate(histories[:3], 1):
                logger.info(f"   记录{i}: {history['input_entity']['name']}")
                logger.info(f"      决策: {history['decision']}")
                logger.info(f"      时间: {history['timestamp']}")
                
            return True
        else:
            logger.error(f"❌ 历史记录测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 历史记录测试异常: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("🚀 开始API测试...")
    
    # 等待服务启动
    logger.info("⏳ 等待服务启动...")
    time.sleep(2)
    
    # 测试用例
    tests = [
        ("健康检查", test_health),
        ("自动决策", test_auto_decide),
        ("候选匹配", test_match_candidates),
        ("统计信息", test_stats),
        ("历史记录", test_history)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 执行测试: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                logger.info(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                logger.error(f"❌ {test_name} 测试失败")
                failed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {e}")
            failed += 1
    
    # 测试总结
    logger.info(f"\n{'='*50}")
    logger.info(f"🎯 测试总结")
    logger.info(f"{'='*50}")
    logger.info(f"✅ 通过: {passed}")
    logger.info(f"❌ 失败: {failed}")
    logger.info(f"📊 成功率: {passed / (passed + failed) * 100:.1f}%")
    
    if failed == 0:
        logger.info("🎉 所有测试都通过了！")
        return True
    else:
        logger.error("⚠️ 有部分测试失败，请检查服务状态")
        return False

if __name__ == "__main__":
    main() 