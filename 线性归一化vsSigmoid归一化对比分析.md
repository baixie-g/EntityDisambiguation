# 线性归一化 vs Sigmoid归一化对比分析

## 🎯 问题背景

在CrossEncoder得分归一化过程中，我们发现sigmoid归一化会导致中等相关的评分过高（接近1.0），这不符合直觉。因此我们将归一化方法改为线性归一化。

## 📊 归一化方法对比

### 1. Sigmoid归一化
```python
def sigmoid_normalize(score: float) -> float:
    return 1 / (1 + np.exp(-score))
```

### 2. 线性归一化
```python
def linear_normalize(score: float) -> float:
    min_score = -6.5
    max_score = 7.7
    normalized = (score - min_score) / (max_score - min_score)
    return max(0.0, min(1.0, normalized))
```

## 📈 实际效果对比

| 匹配类型 | 原始得分 | Sigmoid归一化 | 线性归一化 | 差异 | 说明 |
|----------|----------|---------------|------------|------|------|
| **完全匹配** | 7.7106 | 0.9996 | 1.0000 | -0.0004 | 几乎相同 |
| **高相关** | 4.9174 | 0.9927 | 0.8040 | +0.1887 | 线性更合理 |
| **中等相关** | 3.3470 | 0.9660 | 0.6935 | +0.2725 | 线性更合理 |
| **低相关** | 0.1097 | 0.5274 | 0.4655 | +0.0619 | 线性更合理 |
| **不相关** | -6.5320 | 0.0015 | 0.0000 | +0.0015 | 几乎相同 |

## 🔍 关键发现

### Sigmoid归一化的问题
1. **中等相关得分过高**: 3.3470的原始得分被映射到0.9660，接近完全匹配
2. **高相关得分过高**: 4.9174的原始得分被映射到0.9927，几乎等同于完全匹配
3. **非线性映射**: 在中等分数区间，sigmoid函数变化过于剧烈

### 线性归一化的优势
1. **更直观的映射**: 线性关系，便于理解和调试
2. **合理的得分分布**: 中等相关得分在0.6-0.7区间，符合直觉
3. **保持相对关系**: 原始得分的相对关系得到保持
4. **便于阈值设置**: 得分分布更均匀，便于设置合理的阈值

## 🎯 决策影响分析

### 使用Sigmoid归一化时的决策
- **完全匹配** (0.9996) > 0.85 → 合并 ✅
- **高相关** (0.9927) > 0.85 → 合并 ✅
- **中等相关** (0.9660) > 0.85 → 合并 ❌ (过于激进)
- **低相关** (0.5274) ∈ [0.3, 0.85] → 需要审核 ✅
- **不相关** (0.0015) < 0.3 → 新建 ✅

### 使用线性归一化时的决策
- **完全匹配** (1.0000) > 0.85 → 合并 ✅
- **高相关** (0.8040) ∈ [0.3, 0.85] → 需要审核 ✅ (更合理)
- **中等相关** (0.6935) ∈ [0.3, 0.85] → 需要审核 ✅ (更合理)
- **低相关** (0.4655) ∈ [0.3, 0.85] → 需要审核 ✅
- **不相关** (0.0000) < 0.3 → 新建 ✅

## 📊 加权得分对比

### 测试用例：中等匹配
- BGE: 0.6
- CrossEncoder原始: 3.3470
- Fuzz: 0.7
- Levenshtein: 0.6

### Sigmoid归一化结果
- CrossEncoder归一化: 0.9660
- 加权得分: 0.730
- 状态: 接近合并阈值

### 线性归一化结果
- CrossEncoder归一化: 0.6935
- 加权得分: 0.648
- 状态: 在审核区间

## ✅ 线性归一化的优势总结

### 1. 更合理的得分分布
- 完全匹配: 1.0000 (最高分)
- 高相关: 0.8040 (高分但不过高)
- 中等相关: 0.6935 (中等分数)
- 低相关: 0.4655 (低分)
- 不相关: 0.0000 (最低分)

### 2. 更好的决策支持
- 避免了中等相关被误判为高相关
- 提供了更细粒度的区分能力
- 便于设置合理的阈值

### 3. 更直观的理解
- 线性映射关系清晰
- 便于调试和优化
- 符合人类直觉

### 4. 更好的系统稳定性
- 得分分布更均匀
- 减少了极端值的影响
- 提高了系统的可预测性

## 🎊 结论

线性归一化相比sigmoid归一化具有以下明显优势：

1. **更合理的得分映射**: 中等相关得分不再过高
2. **更好的决策准确性**: 避免了过于激进的合并决策
3. **更直观的理解**: 线性关系便于理解和调试
4. **更稳定的系统行为**: 得分分布更均匀，系统更可预测

因此，线性归一化是CrossEncoder得分处理的最佳选择，能够提供更准确和合理的实体消歧决策支持。 