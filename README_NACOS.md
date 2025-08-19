# Nacos 配置中心集成说明

## 概述

实体消歧服务现已集成 Nacos 配置中心，支持从 Nacos 动态获取 Neo4j 数据库配置，实现配置的集中管理和动态更新。

**技术特点**: 使用基于 `requests` 的轻量级实现，无需额外依赖包，稳定可靠。

## 功能特性

- 🔧 **动态配置获取**: 从 Nacos 获取数据库连接配置
- 🚀 **多数据库支持**: 支持多个 Neo4j 实例的自动发现和连接
- 🔄 **配置热更新**: 支持运行时刷新 Nacos 配置
- 🛡️ **容错机制**: Nacos 不可用时自动回退到本地配置
- 📊 **智能解析**: 自动识别 Neo4j 数据源，忽略 MySQL 等其他类型
- ⚡ **轻量级实现**: 基于 `requests` 库，无需额外依赖

## 技术实现

### 轻量级 Nacos 客户端

- **无外部依赖**: 仅使用项目已有的 `requests` 库
- **HTTP API 调用**: 直接调用 Nacos 的 REST API
- **连接测试**: 启动时自动测试 Nacos 服务可用性
- **超时控制**: 合理的超时设置，避免长时间等待

### 配置获取流程

1. 启动时测试 Nacos 连接
2. 调用 `/nacos/v1/cs/configs` API 获取配置
3. 解析 JSON 配置内容
4. 过滤出有效的 Neo4j 数据源
5. 生成数据库连接配置

## 配置说明

### 1. Nacos 配置项

在 `config/settings.py` 中配置 Nacos 连接信息：

```python
# Nacos配置中心
NACOS_SERVER_ADDR: str = "localhost:8848"      # Nacos服务器地址
NACOS_NAMESPACE: str = ""                       # 命名空间（可选）
NACOS_USERNAME: str = "nacos"                  # 用户名
NACOS_PASSWORD: str = "nacos"                  # 密码
NACOS_DATA_ID: str = "qknow-datasources"       # 配置ID
NACOS_GROUP: str = "DEFAULT_GROUP"             # 配置组
```

### 2. 数据源配置格式

Nacos 中的 `qknow-datasources` 配置应为 JSON 格式：

```json
{
  "datasources": [
    {
      "id": 1,
      "name": "本地Neo4j",
      "type": 2,
      "host": "127.0.0.1",
      "port": 7687,
      "databaseName": "neo4j",
      "username": "neo4j",
      "password": "12345678",
      "status": 1,
      "validFlag": true,
      "delFlag": false
    },
    {
      "id": 2,
      "name": "远端Neo4j-47.105.115.60",
      "type": 2,
      "host": "47.105.115.60",
      "port": 7687,
      "databaseName": "neo4j",
      "username": "neo4j",
      "password": "12345678",
      "status": 1,
      "validFlag": true,
      "delFlag": false
    }
  ]
}
```

**重要说明**:
- `type: 2` 表示 Neo4j 数据源
- `type: 1` 表示 MySQL 数据源（会被自动忽略）
- 只有 `validFlag: true` 且 `delFlag: false` 的数据源才会被使用

## 使用方法

### 1. 启动服务

服务启动时会自动：
1. 连接 Nacos 配置中心
2. 解析数据源配置
3. 创建对应的 Neo4j 连接
4. 初始化数据库服务

### 2. 查看可用数据库

```bash
GET /databases
```

返回示例：
```json
{
  "databases": ["default", "remote"],
  "info": {
    "default": {"entity_count": 1000},
    "remote": {"entity_count": 500}
  },
  "default_key": "default"
}
```

### 3. 指定数据库进行操作

#### 候选匹配
```bash
POST /match-candidates
{
  "entity": {"name": "糖尿病"},
  "top_k": 5,
  "database_key": "remote"
}
```

#### 自动决策
```bash
POST /auto-decide
{
  "entity": {"name": "糖尿病"},
  "force_decision": false,
  "database_key": "remote"
}
```

#### 重建索引
```bash
POST /rebuild-index?database_key=remote
```

### 4. 刷新 Nacos 配置

```bash
POST /refresh-config
```

此接口会：
1. 重新从 Nacos 获取配置
2. 关闭现有数据库连接
3. 使用新配置重新初始化连接

## 数据库键名规则

系统会根据数据源名称自动生成数据库键名：

- 包含"本地"的名称 → `default`
- 包含"远端"的名称 → `remote`
- 其他名称 → 转换为小写，空格和连字符替换为下划线

例如：
- "本地Neo4j" → `default`
- "远端Neo4j-47.105.115.60" → `remote`
- "测试数据库" → `测试数据库`

## 容错机制

### 1. Nacos 不可用
- 自动回退到本地配置（`config/settings.py` 中的 `NEO4J_DATABASES`）
- 记录警告日志，服务继续运行

### 2. 数据库连接失败
- 记录错误日志，跳过该数据库
- 其他数据库正常初始化
- 如果所有数据库都失败，抛出异常

### 3. 配置解析失败
- 记录错误日志
- 使用本地配置作为备选方案

## 监控和日志

### 启动日志示例
```
🔧 Nacos配置中心连接成功
📋 从Nacos获取到 2 个Neo4j数据源
✅ Neo4j服务创建成功[default]: 127.0.0.1:7687
✅ Neo4j服务创建成功[remote]: 47.105.115.60:7687
✅ Neo4j实例初始化完成: ['default', 'remote'], 默认库: default
```

### 配置刷新日志示例
```
🔄 刷新Nacos配置
✅ Nacos配置刷新成功
```

## 测试

运行测试脚本验证 Nacos 配置解析：

```bash
python test_nacos.py
```

## 注意事项

1. **端口配置**: 确保使用正确的 Neo4j Bolt 端口（通常是 7687，不是 7474）
2. **网络连通性**: 确保服务能够访问 Nacos 服务器和所有 Neo4j 实例
3. **权限配置**: 确保 Nacos 账号有读取配置的权限
4. **配置格式**: 严格按照 JSON 格式配置数据源信息
5. **类型过滤**: 系统只会处理 `type=2` 的 Neo4j 数据源

## 故障排除

### 诊断工具

我们提供了一个专门的诊断脚本来帮助排查 Nacos 连接问题：

```bash
python diagnose_nacos.py
```

这个脚本会：
1. 测试基本网络连接
2. 检查各个 Nacos 端点
3. 验证登录认证
4. 测试配置访问权限
5. 提供详细的错误分析和解决建议

### 常见问题

#### 1. HTTP 403 权限不足

**症状**: 日志显示 "从Nacos获取配置失败: HTTP 403"

**可能原因**:
- 用户名或密码错误
- 用户没有读取配置的权限
- 配置不存在或组名错误

**解决方案**:
1. 验证 Nacos 用户名和密码
2. 检查用户是否有读取配置的权限
3. 确认配置ID (`qknow-datasources`) 和组名 (`DEFAULT_GROUP`) 正确
4. 在 Nacos 控制台中手动验证配置访问

#### 2. 连接被拒绝

**症状**: 日志显示 "连接被拒绝" 或 "无法连接到Nacos服务"

**可能原因**:
- Nacos 服务未启动
- 服务器地址或端口错误
- 防火墙阻止连接

**解决方案**:
1. 检查 Nacos 服务状态
2. 验证服务器地址和端口 (默认: localhost:8848)
3. 检查防火墙设置
4. 尝试在浏览器中访问 Nacos 控制台

#### 3. 配置解析失败

**症状**: 日志显示 "解析Neo4j数据源配置失败"

**可能原因**:
- 配置格式不正确
- JSON 解析错误
- 配置内容为空

**解决方案**:
1. 在 Nacos 控制台中检查配置格式
2. 确保配置是有效的 JSON
3. 验证配置包含 `datasources` 数组
4. 检查数据源的必填字段

### 调试模式

启用调试模式可以获得更详细的日志信息：

```python
# 在 config/settings.py 中
NACOS_DEBUG: bool = True
```

调试模式下会输出：
- 详细的连接测试信息
- API 请求和响应详情
- 配置解析过程
- 错误堆栈信息

### 手动验证步骤

1. **检查 Nacos 服务状态**
   ```bash
   # 检查服务是否运行
   curl http://localhost:8848/nacos
   ```

2. **验证用户认证**
   ```bash
   # 尝试登录
   curl -X POST "http://localhost:8848/nacos/v1/auth/users/login" \
        -d "username=nacos&password=nacos"
   ```

3. **手动获取配置**
   ```bash
   # 使用Basic认证获取配置
   curl -u "nacos:nacos" \
        "http://localhost:8848/nacos/v1/cs/configs?dataId=qknow-datasources&group=DEFAULT_GROUP"
   ```

### 日志分析

查看详细日志了解问题：

```bash
# 查看服务日志
tail -f server.out

# 重点关注以下关键词
grep -i "nacos" server.out
grep -i "403\|401\|404" server.out
grep -i "配置\|config" server.out
```

### 联系支持

如果问题仍然存在，请提供以下信息：
1. 诊断脚本的完整输出
2. 服务启动日志
3. Nacos 服务版本
4. 网络环境信息
