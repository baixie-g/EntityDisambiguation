# 实体消歧服务

基于BGE-M3、CrossEncoder、RapidFuzz和编辑距离的实体消歧服务，用于处理从Java后端传来的实体信息，判断其是否为已有实体的重复、是否需要新建，或是否需要人工审核。

## 🚀 功能特性

- **多层次相似度计算**: 结合BGE-M3语义向量、CrossEncoder重排序、RapidFuzz字符串匹配和Levenshtein编辑距离
- **智能消歧决策**: 基于多维度得分和阈值的自动决策系统
- **泛化type字段**: type字段完全泛化，支持任意字符串，用于缩小搜索范围，提高查询效率
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
    "type": "疾病",  # 可选字段，支持预定义类型或自定义字符串
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

**type字段说明:**
- **可选字段**: type字段是可选的，可以不提供
- **完全泛化**: 支持任意字符串，如 "疾病", "症状", "药物", "自定义类型", "特殊分类" 等
- **搜索优化**: 如果提供type，优先在指定类型中搜索；如果没有type或指定类型中无匹配，则在所有实体中搜索
- **无枚举限制**: 不再有预定义的类型限制，完全支持用户自定义分类

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

- **GET** `/health`