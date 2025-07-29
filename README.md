# 实体消歧服务

基于BGE-M3、CrossEncoder、RapidFuzz和编辑距离的实体消歧服务，用于处理从Java后端传来的实体信息，判断其是否为已有实体的重复、是否需要新建，或是否需要人工审核。

## 🚀 功能特性

- **多层次相似度计算**: 结合BGE-M3语义向量、CrossEncoder重排序、RapidFuzz字符串匹配和Levenshtein编辑距离
- **智能消歧决策**: 基于多维度得分和阈值的自动决策系统
- **完整历史记录**: 所有消歧决策都会被记录，支持审计和分析
- **人工审核支持**: 对于歧义情况，标记为需要人工审核
- **REST API**: 提供完整的REST接口，支持自动决策和候选匹配
- **实时索引**: 基于FAISS的高效相似实体检索

## 📋 核心算法流程

1. **BGE-M3编码**: 使用BGE-M3模型对实体名称、别名和定义进行向量化
2. **FAISS检索**: 通过FAISS索引快速检索Top-K相似实体
3. **CrossEncoder重排序**: 使用CrossEncoder对候选实体进行语义重排序
4. **多维度匹配**: 结合RapidFuzz字符串匹配和Levenshtein编辑距离
5. **加权决策**: 综合多个维度得分，根据阈值进行消歧决策

## 🛠 安装配置

### 环境要求

- Python 3.8+
- 4GB+ RAM (推荐8GB以上)
- 2GB+ 存储空间

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd entity-disambiguation
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **初始化数据**
```bash
python init_data.py
```

5. **启动服务**
```bash
python main.py
```

## 📡 API接口

### 1. 自动决策接口

**POST** `/auto-decide`

自动判断实体是否应合并、新建或标记为歧义。

**请求示例:**
```json
{
  "entity": {
    "name": "糖尿病",
    "type": "疾病",
    "aliases": ["diabetes", "糖尿"],
    "definition": "糖尿病是一组以高血糖为特征的代谢性疾病...",
    "attributes": {
      "症状": ["多尿", "口渴", "体重下降"],
      "并发症": ["视网膜病变", "肾病"],
      "治疗方法": ["饮食控制", "胰岛素治疗"]
    },
    "source": "临床指南-2022"
  },
  "force_decision": false
}
```

**响应示例:**
```json
{
  "result": {
    "decision": "merge",
    "match_id": "disease_00001",
    "match_entity": {
      "id": "disease_00001",
      "name": "糖尿病",
      "type": "疾病",
      "aliases": ["diabetes", "糖尿"],
      "definition": "糖尿病是一组以高血糖为特征的代谢性疾病...",
      "attributes": {
        "症状": ["多尿", "多饮", "多食", "体重下降"],
        "并发症": ["糖尿病视网膜病变", "糖尿病肾病"],
        "治疗方法": ["饮食控制", "运动疗法", "药物治疗"]
      },
      "source": "临床指南-2022",
      "create_time": "2024-01-01T10:00:00"
    },
    "scores": {
      "bge_score": 0.92,
      "cross_encoder_score": 0.88,
      "fuzz_score": 0.95,
      "levenshtein_score": 0.90,
      "final_score": 0.91
    },
    "confidence": 0.91,
    "reasoning": "实体名称完全匹配，语义相似度很高，建议合并"
  },
  "message": "自动决策完成"
}
```

### 2. 候选匹配接口

**POST** `/match-candidates`

获取与输入实体相似的候选实体列表。

**请求示例:**
```json
{
  "entity": {
    "name": "糖尿病",
    "type": "疾病",
    "aliases": ["diabetes"],
    "definition": "糖尿病是一组以高血糖为特征的代谢性疾病"
  },
  "top_k": 5,
  "include_scores": true
}
```

### 3. 其他接口

- **GET** `/health` - 健康检查
- **GET** `/stats` - 获取服务统计信息
- **GET** `/history` - 获取消歧历史记录
- **POST** `/rebuild-index` - 重建向量索引

## 🔧 配置说明

主要配置项在 `config/settings.py` 中：

```python
# 相似度阈值
HIGH_THRESHOLD: float = 0.85  # 高于此阈值直接合并
LOW_THRESHOLD: float = 0.65   # 低于此阈值直接新建

# 权重配置
BGE_WEIGHT: float = 0.4           # BGE-M3语义向量权重
CROSS_ENCODER_WEIGHT: float = 0.3  # CrossEncoder重排序权重
FUZZ_WEIGHT: float = 0.2          # RapidFuzz字符串匹配权重
LEVENSHTEIN_WEIGHT: float = 0.1   # Levenshtein编辑距离权重
```

## 📊 数据结构

### 实体格式

```json
{
  "id": "disease_00123",
  "name": "糖尿病",
  "type": "疾病",
  "aliases": ["diabetes", "糖尿"],
  "definition": "糖尿病是一组以高血糖为特征的代谢性疾病...",
  "attributes": {
    "症状": ["多尿", "口渴", "体重下降"],
    "并发症": ["视网膜病变", "肾病"],
    "治疗方法": ["饮食控制", "胰岛素治疗"]
  },
  "source": "临床指南-2022",
  "create_time": "2024-06-10T10:00:00"
}
```

### 决策类型

- **merge**: 合并到已有实体
- **create**: 创建新实体
- **ambiguous**: 歧义，需要人工审核

## 🧪 测试使用

1. **启动服务后访问API文档**
```
http://localhost:8000/docs
```

2. **使用curl测试**
```bash
curl -X POST "http://localhost:8000/auto-decide" \
  -H "Content-Type: application/json" \
  -d '{
    "entity": {
      "name": "糖尿病",
      "type": "疾病",
      "aliases": ["diabetes"],
      "definition": "糖尿病是一组以高血糖为特征的代谢性疾病"
    },
    "force_decision": false
  }'
```

3. **查看健康状态**
```bash
curl http://localhost:8000/health
```

## 📈 性能优化

- 使用FAISS索引加速相似实体检索
- 模型懒加载，减少启动时间
- 支持后台任务，避免阻塞主线程
- 数据库连接池优化
- 向量缓存机制

## 🔍 监控指标

- 实体总数
- 消歧决策统计（合并率、新建率、歧义率）
- 索引状态和维度
- 模型加载状态
- 响应时间统计

## 📝 日志记录

所有消歧决策都会记录到数据库中，包括：
- 输入实体信息
- 决策结果和推理过程
- 各维度相似度得分
- 匹配的实体信息
- 时间戳

## 🚨 注意事项

1. **首次启动**: 需要先运行 `init_data.py` 初始化数据
2. **模型下载**: 首次运行会自动下载BGE-M3和CrossEncoder模型
3. **内存使用**: 模型加载后会占用较多内存，建议至少4GB RAM
4. **索引更新**: 添加新实体后需要重建索引才能被检索到

## 📞 技术支持

如有问题请检查：
1. 日志输出中的错误信息
2. 模型是否正确加载
3. 数据库连接是否正常
4. 向量索引是否构建成功

---

**版本**: 1.0.0  
**更新时间**: 2024-12-19 