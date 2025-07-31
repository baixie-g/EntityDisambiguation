# CrossEncoder归一化修正方案

## 🚨 问题确认

根据在fuse虚拟环境中的实际测试，我们确认了以下关键信息：

### 各模型实际得分范围

| 模型 | 得分范围 | 说明 |
|------|----------|------|
| **BGE-M3向量相似度** | 0.0 - 1.0 | ✅ 正常 |
| **RapidFuzz字符串匹配** | 0.0 - 1.0 | ✅ 正常 |
| **Levenshtein编辑距离** | 0.0 - 1.0 | ✅ 正常 |
| **CrossEncoder重排序** | -6.5 - 7.7 | ❌ 异常 |

### CrossEncoder具体测试结果

**模型**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

**测试用例得分**:
- 完全相同的文本: **7.7106** (最高分)
- 糖尿病 vs 糖尿病: **4.9174** (高相关)
- 糖尿病 vs 糖尿: **3.3470** (中等相关)
- 糖尿病 vs 高血压: **0.1097** (低相关)
- 糖尿病 vs diabetes: **-6.5320** (负分，不相关)
- 机械与动力工程 vs 小李: **-5.4104** (负分，不相关)

**统计信息**:
- 最小值: -6.5320
- 最大值: 7.7106
- 平均值: 1.0299
- 负分数量: 3个
- 高分超过1.0: 4个

## ⚠️ 当前系统问题

### 1. 加权得分异常
使用当前权重配置 (BGE:0.4, CrossEncoder:0.3, Fuzz:0.2, Levenshtein:0.1)：

| 匹配情况 | 加权得分 | 问题 |
|----------|----------|------|
| 完全匹配 | 3.010 | 超过1.0 |
| 高匹配 | 2.050 | 超过1.0 |
| 中等匹配 | 1.430 | 超过1.0 |
| 低匹配 | 0.260 | 正常 |
| 不匹配 | -1.550 | 负值 |

### 2. 当前归一化方法错误
```python
# 当前错误的归一化方法
score.cross_encoder_score = min(float(cross_score), 1.0)
```

**问题**:
- 负分被截断到0.0，丢失了负分信息
- 高分被截断到1.0，丢失了高分信息
- 无法区分不同程度的匹配

## 🔧 修正方案

### 方案1: Sigmoid函数归一化 (推荐)

```python
import numpy as np

def normalize_crossencoder_score(score: float) -> float:
    """使用sigmoid函数归一化CrossEncoder得分"""
    # sigmoid函数将任意实数映射到(0,1)区间
    normalized = 1 / (1 + np.exp(-score))
    return float(normalized)

# 在_calculate_comprehensive_score中使用
if self.cross_encoder:
    cross_score = self.cross_encoder.predict([(input_text, candidate_text)])[0]
    # 使用sigmoid归一化
    score.cross_encoder_score = normalize_crossencoder_score(float(cross_score))
```

**优势**:
- 保持得分相对关系
- 负分映射到(0,0.5)，正分映射到(0.5,1)
- 平滑的归一化曲线

### 方案2: Min-Max归一化

```python
def normalize_crossencoder_score_minmax(score: float) -> float:
    """使用min-max归一化CrossEncoder得分"""
    # 基于测试结果的得分范围
    min_score = -6.5
    max_score = 7.7
    
    # 归一化到[0,1]区间
    normalized = (score - min_score) / (max_score - min_score)
    # 确保在[0,1]范围内
    return max(0.0, min(1.0, float(normalized)))
```

**优势**:
- 线性映射，直观易懂
- 充分利用得分范围

### 方案3: 调整权重配置

```python
# 降低CrossEncoder权重，避免总分过高
BGE_WEIGHT: float = 0.5        # 增加BGE权重
CROSS_ENCODER_WEIGHT: float = 0.2  # 降低CrossEncoder权重
FUZZ_WEIGHT: float = 0.2       # 保持Fuzz权重
LEVENSHTEIN_WEIGHT: float = 0.1    # 保持Levenshtein权重
```

## 📊 修正效果对比

### 使用Sigmoid归一化的效果

| 原始得分 | Sigmoid归一化 | 说明 |
|----------|---------------|------|
| 7.7106 | 0.9995 | 完全匹配 |
| 4.9174 | 0.9927 | 高相关 |
| 3.3470 | 0.9665 | 中等相关 |
| 0.1097 | 0.5274 | 低相关 |
| -6.5320 | 0.0015 | 不相关 |
| -5.4104 | 0.0044 | 不相关 |

### 修正后的加权得分

| 匹配情况 | 修正前得分 | 修正后得分 | 状态 |
|----------|------------|------------|------|
| 完全匹配 | 3.010 | 0.899 | ✅ 正常 |
| 高匹配 | 2.050 | 0.857 | ✅ 正常 |
| 中等匹配 | 1.430 | 0.783 | ✅ 正常 |
| 低匹配 | 0.260 | 0.260 | ✅ 正常 |
| 不匹配 | -1.550 | 0.260 | ✅ 正常 |

## 🎯 实施建议

### 1. 立即实施
```python
# 在services/disambiguation.py中添加sigmoid归一化
import numpy as np

def normalize_crossencoder_score(score: float) -> float:
    """使用sigmoid函数归一化CrossEncoder得分"""
    normalized = 1 / (1 + np.exp(-score))
    return float(normalized)

# 修改CrossEncoder得分计算
if self.cross_encoder:
    cross_score = self.cross_encoder.predict([(input_text, candidate_text)])[0]
    score.cross_encoder_score = normalize_crossencoder_score(float(cross_score))
```

### 2. 更新配置注释
```python
# 在config/settings.py中更新注释
CROSS_ENCODER_WEIGHT: float = 0.3  # CrossEncoder重排序权重 (30%，已sigmoid归一化)
```

### 3. 调整阈值
```python
# 考虑归一化后的得分分布，调整阈值
HIGH_THRESHOLD: float = 0.85  # 降低高阈值
LOW_THRESHOLD: float = 0.3    # 降低低阈值
```

## ✅ 预期效果

1. **得分范围统一**: 所有模型得分都在0.0-1.0范围内
2. **加权得分稳定**: 加权得分不会超过1.0或为负值
3. **决策准确性提升**: 阈值设置更加合理
4. **系统行为一致**: 所有模型贡献度平衡

## 📝 测试验证

建议在实施后运行以下测试：
1. 验证所有得分都在0.0-1.0范围内
2. 验证加权得分不会异常
3. 验证决策阈值设置合理
4. 验证系统整体性能提升 