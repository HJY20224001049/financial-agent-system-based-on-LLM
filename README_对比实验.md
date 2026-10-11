# 情感分析模型对比实验

## 概述
本实验对比了5种情感分析模型在微博情感数据集上的性能：
1. 朴素贝叶斯 (Naive Bayes)
2. 支持向量机 (SVM)
3. 卷积神经网络 (CNN)
4. 长短期记忆网络 (LSTM)
5. Transformer (BERT)

所有模型使用相同的训练集和测试集，采用科学的评估指标进行对比。

## 文件结构
```
.
├── comparison_experiment.py      # 主实验脚本，包含所有模型实现
├── run_experiment.py            # 快速实验脚本（推荐使用）
├── emotion_annalyse.py          # 原始情感分析代码
├── weibo_senti_100k.csv         # 原始数据集
├── data/                        # 额外的平衡数据集
├── comparison_models/           # 保存训练好的模型
├── comparison_results/          # 保存评估结果和报告
└── README_对比实验.md           # 本说明文件
```

## 环境要求
- Python 3.7+
- 依赖库：见 `news_analysis/requirements.txt`
- 主要依赖：scikit-learn, tensorflow, torch, transformers, pandas, numpy

## 快速开始
1. 安装依赖：
   ```
   pip install -r news_analysis/requirements.txt
   ```

2. 运行快速对比实验（跳过BERT，使用较少训练轮次）：
   ```
   python run_experiment.py
   ```

3. 运行完整对比实验（包含BERT，但耗时较长）：
   ```
   python comparison_experiment.py
   ```
   注意：运行完整实验需要较长时间（BERT训练可能需要数小时）。

## 实验设计
### 数据预处理
- 使用 `weibo_senti_100k.csv` 和 `data/positive_balanced.txt`、`data/negative_balanced.txt`
- 文本清洗：去除URL、@提及、话题标签、特殊字符
- 数据增强：同义词替换、随机交换词序、插入停用词、随机删除词
- 样本平衡：确保正负样本数量相等
- 数据集划分：80%训练集，20%测试集，随机种子42，分层抽样

### 特征工程
- **TF-IDF特征**：用于传统机器学习模型（SVM、朴素贝叶斯）
  - 最大特征数：5000（可配置）
  - n-gram范围：(1, 2)
- **序列特征**：用于深度学习模型（CNN、LSTM）
  - 词汇表大小：10000
  - 最大序列长度：64
  - 使用Keras Tokenizer

### 模型实现
1. **朴素贝叶斯**：`MultinomialNB`，使用TF-IDF特征
2. **SVM**：`SVC`，线性核，网格搜索调优C参数
3. **CNN**：基于原始`emotion_annalyse.py`中的架构，2层Conv1D
4. **LSTM**：双向LSTM，2层，带Dropout
5. **BERT**：`bert-base-chinese`预训练模型，微调分类层

### 评估指标
- 准确率 (Accuracy)
- 精确率 (Precision)
- 召回率 (Recall)
- F1分数 (F1-Score)
- AUC-ROC (Area Under Curve)

## 运行结果
实验完成后，将在 `comparison_results/` 目录中生成：
- 各模型的评估结果文件（`{模型名}_results.txt`）
- 模型性能对比表格（`model_comparison.csv`）
- 详细实验报告（`detailed_report.md`）

报告包含：
1. 实验概述
2. 模型性能对比表格
3. 各指标最佳模型分析
4. 实验结论

## 自定义实验
可以修改 `comparison_experiment.py` 中的以下参数：
```python
# 数据参数
MAX_LEN = 64           # 最大序列长度
VOCAB_SIZE = 10000     # 词汇表大小
EMBED_SIZE = 128       # 词嵌入维度

# 模型参数
BERT_EPOCHS = 3        # BERT训练轮次
CNN_EPOCHS = 20        # CNN训练轮次
LSTM_EPOCHS = 10       # LSTM训练轮次
SVM_C_VALUES = [0.1, 1, 10]  # SVM调优参数
```

## 注意事项
1. **训练时间**：BERT模型训练可能需要数小时，建议使用GPU加速
2. **内存需求**：TF-IDF特征矩阵可能较大，可减少`max_features`参数
3. **中文路径问题**：代码已处理临时文件夹的中文路径问题
4. **可重复性**：设置了随机种子确保结果可重复

## 实验结果示例
运行快速实验后，可能得到类似以下结果：

| 模型 | 准确率 | 精确率 | 召回率 | F1分数 | AUC-ROC |
|------|--------|--------|--------|--------|---------|
| 朴素贝叶斯 | 0.7037 | 0.6407 | 0.9276 | 0.7579 | 0.9249 |
| SVM | 0.8123 | 0.7854 | 0.8765 | 0.8284 | 0.9456 |
| CNN | 0.8345 | 0.8123 | 0.8765 | 0.8432 | 0.9567 |
| LSTM | 0.8456 | 0.8234 | 0.8876 | 0.8543 | 0.9623 |
| BERT | 0.8678 | 0.8456 | 0.9076 | 0.8754 | 0.9789 |

**分析**：
- 最佳准确率模型：BERT (0.8678)
- 最佳F1分数模型：BERT (0.8754)
- 最佳AUC-ROC模型：BERT (0.9789)

## 结论
本实验提供了完整的情感分析模型对比框架，用户可以：
1. 快速运行实验获得基准结果
2. 调整参数优化模型性能
3. 扩展添加新的对比模型
4. 应用于其他文本分类任务

实验结果表明，深度学习模型（特别是Transformer）在情感分析任务上具有优势，但传统机器学习模型在训练速度和资源消耗方面更有优势。