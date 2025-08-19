#!/usr/bin/env python3
"""
Nacos连接诊断脚本
"""
import requests
import json
import sys
import os
from urllib.parse import urlparse

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings

def test_basic_connectivity():
    """测试基本连接性"""
    print("🔍 测试基本连接性...")
    
    base_url = f"http://{settings.NACOS_SERVER_ADDR}"
    print(f"   目标地址: {base_url}")
    
    try:
        # 测试HTTP连接
        response = requests.get(base_url, timeout=5)
        print(f"   HTTP连接: ✅ (状态码: {response.status_code})")
        return True
    except requests.exceptions.ConnectionError:
        print(f"   HTTP连接: ❌ 连接被拒绝")
        return False
    except requests.exceptions.Timeout:
        print(f"   HTTP连接: ❌ 连接超时")
        return False
    except Exception as e:
        print(f"   HTTP连接: ❌ 异常: {e}")
        return False

def test_nacos_endpoints():
    """测试Nacos各个端点"""
    print("\n🔍 测试Nacos端点...")
    
    base_url = f"http://{settings.NACOS_SERVER_ADDR}"
    auth = (settings.NACOS_USERNAME, settings.NACOS_PASSWORD)
    
    endpoints = [
        ("/nacos", "根路径"),
        ("/nacos/v1/console/namespaces", "命名空间API"),
        ("/nacos/v1/auth/users/login", "登录API"),
        ("/nacos/v1/cs/configs", "配置API"),
        ("/nacos/v2/cs/configs", "配置API v2")
    ]
    
    results = {}
    
    for endpoint, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            print(f"   测试 {description}: {endpoint}")
            
            # 先测试无认证
            response_no_auth = requests.get(url, timeout=5)
            print(f"     无认证: HTTP {response_no_auth.status_code}")
            
            # 再测试Basic认证
            response_auth = requests.get(url, auth=auth, timeout=5)
            print(f"     Basic认证: HTTP {response_auth.status_code}")
            
            if response_auth.status_code == 200:
                print(f"     ✅ 端点可用")
                results[endpoint] = "可用"
            elif response_auth.status_code in [401, 403]:
                print(f"     ⚠️ 端点需要认证或权限不足")
                results[endpoint] = "需要认证"
            else:
                print(f"     ❌ 端点不可用")
                results[endpoint] = "不可用"
                
        except Exception as e:
            print(f"     ❌ 测试失败: {e}")
            results[endpoint] = "失败"
    
    return results

def test_config_access():
    """测试配置访问"""
    print("\n🔍 测试配置访问...")
    
    base_url = f"http://{settings.NACOS_SERVER_ADDR}"
    auth = (settings.NACOS_USERNAME, settings.NACOS_PASSWORD)
    
    # 尝试获取认证token
    print("   获取认证token...")
    token = test_login()
    
    # 尝试获取配置
    config_url = f"{base_url}/nacos/v1/cs/configs"
    params = {
        'dataId': settings.NACOS_DATA_ID,
        'group': settings.NACOS_GROUP,
        'tenant': settings.NACOS_NAMESPACE if settings.NACOS_NAMESPACE else ''
    }
    
    print(f"   配置ID: {settings.NACOS_DATA_ID}")
    print(f"   配置组: {settings.NACOS_GROUP}")
    print(f"   命名空间: {settings.NACOS_NAMESPACE or '默认'}")
    
    try:
        # 无认证
        response_no_auth = requests.get(config_url, params=params, timeout=10)
        print(f"   无认证请求: HTTP {response_no_auth.status_code}")
        
        # Basic认证
        response_auth = requests.get(config_url, params=params, auth=auth, timeout=10)
        print(f"   Basic认证请求: HTTP {response_auth.status_code}")
        
        # Bearer Token认证
        if token:
            headers = {'Authorization': f'Bearer {token}'}
            response_token = requests.get(config_url, params=params, headers=headers, timeout=10)
            print(f"   Bearer Token认证请求: HTTP {response_token.status_code}")
            
            if response_token.status_code == 200:
                config_content = response_token.text
                if config_content:
                    try:
                        config_data = json.loads(config_content)
                        print(f"   ✅ 配置获取成功 (Bearer Token)")
                        print(f"   配置内容长度: {len(config_content)} 字符")
                        if 'datasources' in config_data:
                            print(f"   数据源数量: {len(config_data['datasources'])}")
                        return True
                    except json.JSONDecodeError:
                        print(f"   ❌ 配置内容不是有效JSON")
                        return False
                else:
                    print(f"   ⚠️ 配置内容为空")
                    return False
            else:
                print(f"   ❌ Bearer Token认证失败: HTTP {response_token.status_code}")
        
        # 检查其他认证方式的结果
        if response_auth.status_code == 200:
            config_content = response_auth.text
            if config_content:
                try:
                    config_data = json.loads(config_content)
                    print(f"   ✅ 配置获取成功 (Basic Auth)")
                    print(f"   配置内容长度: {len(config_content)} 字符")
                    if 'datasources' in config_data:
                        print(f"   数据源数量: {len(config_data['datasources'])}")
                    return True
                except json.JSONDecodeError:
                    print(f"   ❌ 配置内容不是有效JSON")
                    return False
            else:
                print(f"   ⚠️ 配置内容为空")
                return False
        elif response_auth.status_code == 403:
            print(f"   ❌ 权限不足 (403)")
            print(f"   可能原因:")
            print(f"     - 用户名或密码错误")
            print(f"     - 用户没有读取配置的权限")
            print(f"     - 配置不存在或组名错误")
            return False
        elif response_auth.status_code == 404:
            print(f"   ❌ 配置不存在 (404)")
            print(f"   可能原因:")
            print(f"     - 配置ID错误: {settings.NACOS_DATA_ID}")
            print(f"     - 配置组错误: {settings.NACOS_GROUP}")
            print(f"     - 命名空间错误: {settings.NACOS_NAMESPACE}")
            return False
        else:
            print(f"   ❌ 未知错误: HTTP {response_auth.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False

def test_login():
    """测试登录认证"""
    print("\n🔍 测试登录认证...")
    
    base_url = f"http://{settings.NACOS_SERVER_ADDR}"
    login_data = {
        'username': settings.NACOS_USERNAME,
        'password': settings.NACOS_PASSWORD
    }
    
    try:
        login_url = f"{base_url}/nacos/v1/auth/users/login"
        response = requests.post(login_url, data=login_data, timeout=10)
        
        print(f"   登录请求: HTTP {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('accessToken'):
                    print(f"   ✅ 登录成功，获取到token")
                    print(f"   Token长度: {len(result['accessToken'])}")
                    return result['accessToken']
                else:
                    print(f"   ⚠️ 登录成功但未获取到token")
                    print(f"   响应内容: {result}")
                    return None
            except json.JSONDecodeError:
                print(f"   ❌ 登录响应不是有效JSON")
                return None
        elif response.status_code == 401:
            print(f"   ❌ 用户名或密码错误")
            return None
        else:
            print(f"   ❌ 登录失败: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ❌ 登录测试失败: {e}")
        return None

def main():
    """主函数"""
    print("🚀 Nacos连接诊断工具")
    print("=" * 50)
    
    # 显示配置信息
    print(f"🔧 配置信息:")
    print(f"   服务器地址: {settings.NACOS_SERVER_ADDR}")
    print(f"   用户名: {settings.NACOS_USERNAME}")
    print(f"   密码: {'*' * len(settings.NACOS_PASSWORD)}")
    print(f"   配置ID: {settings.NACOS_DATA_ID}")
    print(f"   配置组: {settings.NACOS_GROUP}")
    print(f"   命名空间: {settings.NACOS_NAMESPACE or '默认'}")
    
    # 测试基本连接
    if not test_basic_connectivity():
        print("\n❌ 基本连接失败，请检查:")
        print("   - Nacos服务是否启动")
        print("   - 服务器地址和端口是否正确")
        print("   - 网络连接是否正常")
        return
    
    # 测试端点
    endpoint_results = test_nacos_endpoints()
    
    # 测试登录
    token = test_login()
    
    # 测试配置访问
    config_ok = test_config_access()
    
    # 总结
    print("\n📋 诊断总结:")
    print("=" * 50)
    
    if config_ok:
        print("✅ 配置访问正常")
    else:
        print("❌ 配置访问失败")
        
        if not any(r == "可用" for r in endpoint_results.values()):
            print("   - 所有Nacos端点都不可用")
        elif not token:
            print("   - 登录认证失败")
        else:
            print("   - 配置访问权限不足")
    
    print("\n💡 建议:")
    if not config_ok:
        print("   1. 检查Nacos服务状态")
        print("   2. 验证用户名密码")
        print("   3. 确认配置ID和组名")
        print("   4. 检查用户权限设置")
        print("   5. 查看Nacos服务日志")

if __name__ == "__main__":
    main()
