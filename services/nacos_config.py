"""
Nacos配置中心服务 - 基于requests的轻量级实现
"""
import json
import logging
import requests
from typing import Dict, List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class NacosConfigService:
    """Nacos配置中心服务类 - 轻量级实现"""
    
    def __init__(self):
        self.base_url = f"http://{settings.NACOS_SERVER_ADDR}"
        self.auth = (settings.NACOS_USERNAME, settings.NACOS_PASSWORD)
        self.config_cache = None
        self.client_available = False
        self.init_client()
    
    def init_client(self):
        """初始化Nacos客户端"""
        try:
            logger.info(f"🔧 初始化Nacos客户端: {self.base_url}")
            logger.info(f"🔧 认证信息: {settings.NACOS_USERNAME}@{settings.NACOS_SERVER_ADDR}")
            
            # 测试连接 - 尝试多个可能的API端点
            test_endpoints = [
                "/nacos/v1/console/namespaces",
                "/nacos/v1/auth/users/login",
                "/nacos/v1/cs/configs"
            ]
            
            for endpoint in test_endpoints:
                try:
                    if settings.NACOS_DEBUG:
                        logger.debug(f"🔍 测试端点: {endpoint}")
                    
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        auth=self.auth,
                        timeout=5
                    )
                    
                    if settings.NACOS_DEBUG:
                        logger.debug(f"🔍 端点 {endpoint} 响应: HTTP {response.status_code}")
                        if response.status_code != 200:
                            logger.debug(f"🔍 响应内容: {response.text[:200]}")
                    
                    if response.status_code in [200, 401, 403]:  # 这些状态码表示服务可达
                        logger.info(f"✅ Nacos服务可达: {endpoint} (HTTP {response.status_code})")
                        self.client_available = True
                        break
                except Exception as e:
                    if settings.NACOS_DEBUG:
                        logger.debug(f"🔍 测试端点 {endpoint} 失败: {e}")
                    continue
            
            if not self.client_available:
                logger.warning("⚠️ 无法连接到Nacos服务")
                
        except Exception as e:
            logger.warning(f"⚠️ Nacos客户端初始化失败: {e}")
            self.client_available = False
    
    def _get_auth_token(self) -> Optional[str]:
        """获取认证token（如果需要）"""
        try:
            login_url = f"{self.base_url}/nacos/v1/auth/users/login"
            login_data = {
                'username': settings.NACOS_USERNAME,
                'password': settings.NACOS_PASSWORD
            }
            
            response = requests.post(
                login_url,
                data=login_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('accessToken'):
                    logger.info("✅ 获取Nacos认证token成功")
                    return result['accessToken']
            
            logger.debug(f"获取认证token失败: HTTP {response.status_code}")
            return None
            
        except Exception as e:
            logger.debug(f"获取认证token异常: {e}")
            return None
    
    def get_datasources_config(self) -> Optional[Dict]:
        """获取数据源配置"""
        if not self.client_available:
            logger.warning("Nacos客户端未初始化或不可用")
            return None
        
        try:
            # 尝试获取认证token
            auth_token = self._get_auth_token()
            
            # 构建请求头
            headers = {}
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
                if settings.NACOS_DEBUG:
                    logger.debug(f"🔍 使用Bearer Token认证: {auth_token[:20]}...")
            
            # 尝试多种配置获取方式
            config_urls = [
                f"{self.base_url}/nacos/v1/cs/configs",
                f"{self.base_url}/nacos/v2/cs/configs"
            ]
            
            for url in config_urls:
                try:
                    params = {
                        'dataId': settings.NACOS_DATA_ID,
                        'group': settings.NACOS_GROUP,
                        'tenant': settings.NACOS_NAMESPACE if settings.NACOS_NAMESPACE else ''
                    }
                    
                    if settings.NACOS_DEBUG:
                        logger.debug(f"🔍 尝试获取配置: {url} 参数: {params}")
                    
                    # 优先使用Bearer Token认证
                    if auth_token:
                        response = requests.get(
                            url, 
                            params=params, 
                            headers=headers,
                            timeout=10
                        )
                    else:
                        # 如果没有token，使用Basic Auth
                        response = requests.get(
                            url, 
                            params=params, 
                            auth=self.auth,
                            timeout=10
                        )
                    
                    if settings.NACOS_DEBUG:
                        logger.debug(f"🔍 配置获取响应: HTTP {response.status_code}")
                        if response.status_code != 200:
                            logger.debug(f"🔍 响应内容: {response.text[:200]}")
                    
                    if response.status_code == 200:
                        config_content = response.text
                        if config_content:
                            # 解析JSON配置
                            config_data = json.loads(config_content)
                            logger.info(f"✅ 从Nacos获取配置成功: {settings.NACOS_DATA_ID}")
                            self.config_cache = config_data
                            return config_data
                        else:
                            logger.warning("⚠️ 从Nacos获取配置为空")
                            return None
                    elif response.status_code == 403:
                        logger.error(f"❌ 权限不足，请检查用户名密码和权限设置")
                        # 尝试不带认证的请求
                        try:
                            response_no_auth = requests.get(url, params=params, timeout=10)
                            if response_no_auth.status_code == 200:
                                logger.info("✅ 无认证方式获取配置成功")
                                config_content = response_no_auth.text
                                if config_content:
                                    config_data = json.loads(config_content)
                                    self.config_cache = config_data
                                    return config_data
                        except Exception as e:
                            if settings.NACOS_DEBUG:
                                logger.debug(f"🔍 无认证请求失败: {e}")
                        return None
                    else:
                        if settings.NACOS_DEBUG:
                            logger.debug(f"🔍 配置获取失败: HTTP {response.status_code}")
                        continue
                        
                except Exception as e:
                    if settings.NACOS_DEBUG:
                        logger.debug(f"🔍 尝试 {url} 失败: {e}")
                    continue
            
            logger.error("❌ 所有配置获取方式都失败")
            return None
                
        except Exception as e:
            logger.error(f"❌ 从Nacos获取配置失败: {e}")
            return None
    
    def parse_neo4j_datasources(self) -> Dict[str, Dict]:
        """解析Neo4j数据源配置"""
        config = self.get_datasources_config()
        if not config:
            logger.warning("⚠️ 无法获取Nacos配置，使用本地配置")
            return settings.NEO4J_DATABASES
        
        try:
            neo4j_dbs = {}
            datasources = config.get('datasources', [])
            
            logger.info(f"📋 解析数据源配置，共 {len(datasources)} 个数据源")
            
            for ds in datasources:
                ds_id = ds.get('id')
                ds_type = ds.get('type')
                ds_name = ds.get('name', 'Unknown')
                ds_status = ds.get('status', 0)
                ds_valid = ds.get('validFlag', False)
                ds_deleted = ds.get('delFlag', False)
                
                # 只处理Neo4j类型的数据源 (type=2)，忽略MySQL等其他类型
                if ds_type == 2 and ds_valid and not ds_deleted and ds_status == 1:
                    host = ds.get('host', '')
                    port = ds.get('port', 7687)
                    database = ds.get('databaseName', 'neo4j')
                    username = ds.get('username', 'neo4j')
                    password = ds.get('password', '')
                    
                    if host and username and password and ds_id:
                        # 使用数据库ID作为键名
                        db_key = str(ds_id)
                        
                        neo4j_dbs[db_key] = {
                            'id': ds_id,
                            'uri': f"bolt://{host}:{port}",
                            'user': username,
                            'password': password,
                            'database': database,
                            'name': ds_name,
                            'host': host,
                            'port': port,
                            'remark': ds.get('remark', ''),
                            'status': ds_status,
                            'valid_flag': ds_valid,
                            'del_flag': ds_deleted
                        }
                        
                        logger.info(f"✅ 解析Neo4j数据源: {db_key} -> {ds_name} ({host}:{port})")
                else:
                    # 记录忽略的数据源类型
                    if ds_type == 1:
                        logger.info(f"ℹ️ 忽略MySQL数据源: {ds_name}")
                    elif ds_type != 2:
                        logger.info(f"ℹ️ 忽略未知类型数据源: {ds_name} (type={ds_type})")
                    elif not ds_valid:
                        logger.info(f"ℹ️ 忽略无效数据源: {ds_name} (validFlag={ds_valid})")
                    elif ds_deleted:
                        logger.info(f"ℹ️ 忽略已删除数据源: {ds_name} (delFlag={ds_deleted})")
                    elif ds_status != 1:
                        logger.info(f"ℹ️ 忽略非启用状态数据源: {ds_name} (status={ds_status})")
            
            if not neo4j_dbs:
                logger.warning("⚠️ 未找到有效的Neo4j数据源，使用本地配置")
                return settings.NEO4J_DATABASES
            
            logger.info(f"✅ 成功解析 {len(neo4j_dbs)} 个Neo4j数据源")
            return neo4j_dbs
            
        except Exception as e:
            logger.error(f"❌ 解析Neo4j数据源配置失败: {e}")
            return settings.NEO4J_DATABASES
    
    def get_default_database_key(self) -> str:
        """获取默认数据库键名"""
        neo4j_dbs = self.parse_neo4j_datasources()
        if neo4j_dbs:
            # 优先选择包含"本地"或"默认"的数据库
            for db_key, db_info in neo4j_dbs.items():
                db_name = db_info.get('name', '')
                if '本地' in db_name or '默认' in db_name:
                    logger.info(f"✅ 选择默认数据库: {db_key} ({db_name})")
                    return db_key
            
            # 如果没有找到本地/默认数据库，返回第一个可用的
            first_key = list(neo4j_dbs.keys())[0]
            first_name = neo4j_dbs[first_key].get('name', 'Unknown')
            logger.info(f"✅ 选择第一个可用数据库作为默认: {first_key} ({first_name})")
            return first_key
        else:
            logger.warning("⚠️ 没有可用的Neo4j数据库，使用配置中的默认值")
            return settings.DEFAULT_NEO4J_KEY
    
    def refresh_config(self):
        """刷新配置"""
        logger.info("🔄 刷新Nacos配置")
        self.config_cache = None
        return self.parse_neo4j_datasources()
    
    def is_available(self) -> bool:
        """检查Nacos服务是否可用"""
        return self.client_available

# 全局Nacos配置服务实例
nacos_config_service = NacosConfigService()
