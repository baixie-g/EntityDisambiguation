# 数据库命名规范与接口使用说明

## 🎯 设计原则

为了同时管理多个数据库，我们采用了以下设计原则：

1. **数据库标识使用 ID**：如 `1`, `2`, `3` 等，确保唯一性和一致性
2. **接口显示包含数据库名称描述**：让用户看到友好的名称和详细信息
3. **操作时使用 ID**：确保精确性和避免歧义

## 🔧 数据库键名规则

### 从 Nacos 配置获取
- **ID**: 使用 Nacos 中配置的 `id` 字段作为数据库键名
- **名称**: 使用 Nacos 中配置的 `name` 字段作为显示名称
- **描述**: 使用 Nacos 中配置的 `remark` 字段作为备注信息

### 示例配置
```json
{
  "datasources": [
    {
      "id": 1,
      "name": "本地Neo4j",
      "remark": "默认本地Neo4j",
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
      "remark": "远端Neo4j",
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

### 生成的数据库键名
- **数据库 1**: 键名 `"1"`, 名称 `"本地Neo4j"`
- **数据库 2**: 键名 `"2"`, 名称 `"远端Neo4j-47.105.115.60"`

## 📋 API 接口使用

### 1. 获取数据库列表
```bash
GET /databases
```

**响应示例**:
```json
{
  "databases": [
    {
      "id": "1",
      "name": "本地Neo4j",
      "host": "127.0.0.1",
      "port": 7687,
      "database": "neo4j",
      "entity_count": 0,
      "status": "connected",
      "remark": "默认本地Neo4j"
    },
    {
      "id": "2",
      "name": "远端Neo4j-47.105.115.60",
      "host": "47.105.115.60",
      "port": 7687,
      "database": "neo4j",
      "entity_count": 0,
      "status": "connected",
      "remark": "远端Neo4j"
    }
  ],
  "database_ids": ["1", "2"],
  "default_key": "1",
  "total_count": 2,
  "message": "成功获取 2 个数据库信息"
}
```

### 2. 指定数据库进行操作

#### 匹配候选实体
```bash
POST /match-candidates
Content-Type: application/json

{
  "entity": {
    "name": "测试实体",
    "type": "Person"
  },
  "database_key": "2"  # 使用数据库ID
}
```

#### 自动决策
```bash
POST /auto-decide
Content-Type: application/json

{
  "entity": {
    "name": "测试实体",
    "type": "Person"
  },
  "database_key": "1"  # 使用数据库ID
}
```

#### 重建索引
```bash
POST /rebuild-index?database_key=2
```

## 🔍 接口字段说明

### 数据库信息字段
- **`id`**: 数据库唯一标识符，用于所有API操作
- **`name`**: 数据库友好名称，用于显示
- **`host`**: 数据库主机地址
- **`port`**: 数据库端口
- **`database`**: 数据库名称
- **`entity_count`**: 当前实体数量
- **`status`**: 连接状态 (`connected`, `error`)
- **`remark`**: 数据库备注信息

### 操作参数
- **`database_key`**: 目标数据库ID，不填则使用默认数据库

## 💡 使用建议

### 1. 前端显示
- 在界面上显示数据库名称和描述信息
- 提供数据库选择下拉框，显示名称但传递ID
- 显示数据库的连接状态和实体数量

### 2. API 调用
- 始终使用数据库ID进行API调用
- 在请求参数中使用 `database_key` 字段
- 如果不指定，系统将使用默认数据库

### 3. 错误处理
- 如果指定的数据库ID不存在，API会返回错误
- 检查 `/databases` 接口获取有效的数据库ID列表

## 🔄 配置更新

### 刷新 Nacos 配置
```bash
POST /refresh-config
```

### 配置变更后的行为
- 数据库ID保持不变，确保API调用的稳定性
- 数据库名称和描述信息会更新
- 新增的数据库会获得新的ID
- 删除的数据库会从列表中移除

## 📝 示例代码

### Python 客户端示例
```python
import requests

# 获取数据库列表
response = requests.get("http://localhost:8002/databases")
databases = response.json()

# 显示数据库信息
for db in databases["databases"]:
    print(f"ID: {db['id']}, 名称: {db['name']}, 状态: {db['status']}")

# 在指定数据库中搜索实体
database_id = "2"  # 使用数据库ID
response = requests.post(
    "http://localhost:8002/match-candidates",
    json={
        "entity": {"name": "测试", "type": "Person"},
        "database_key": database_id
    }
)
```

### JavaScript 客户端示例
```javascript
// 获取数据库列表
const response = await fetch('/databases');
const data = await response.json();

// 显示数据库选择器
data.databases.forEach(db => {
    console.log(`ID: ${db.id}, 名称: ${db.name}`);
});

// 在指定数据库中操作
const databaseId = "2";
const result = await fetch('/match-candidates', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        entity: {name: "测试", type: "Person"},
        database_key: databaseId
    })
});
```

## ✅ 优势总结

1. **唯一性**: 使用ID确保数据库标识的唯一性
2. **可读性**: 接口返回详细的数据库信息，便于用户理解
3. **稳定性**: 数据库ID相对稳定，减少API调用的影响
4. **扩展性**: 支持动态添加和删除数据库
5. **一致性**: 所有API操作都使用统一的ID标识方式
