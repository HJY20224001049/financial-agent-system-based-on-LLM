"""
对比实验：5种情感分析模型性能比较
包括：逻辑回归, 朴素贝叶斯, CNN, LSTM, Transformer (BERT)
使用相同的数据集和评估指标
"""

import os
import sys
import pickle
import numpy as np
import pandas as pd
import re
import random
from chardet import detect

# 机器学习库
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, fbeta_score, roc_auc_score, confusion_matrix, mean_absolute_error, mean_squared_error, r2_score, matthews_corrcoef, cohen_kappa_score, balanced_accuracy_score, jaccard_score, hamming_loss, zero_one_loss, log_loss, brier_score_loss
# 尝试导入mean_absolute_percentage_error，如果不可用则自定义
try:
    from sklearn.metrics import mean_absolute_percentage_error
except ImportError:
    # 自定义MAPE函数
    def mean_absolute_percentage_error(y_true, y_pred):
        epsilon = 1e-10
        return np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + epsilon))) * 100

# 深度学习库
import tensorflow as tf
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.layers import Embedding, Dense, Conv1D, MaxPool1D, Flatten, Dropout, BatchNormalization, LSTM, Bidirectional
from tensorflow.keras.models import Sequential
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2
from tensorflow.keras.activations import gelu

# Transformer库
import torch
from transformers import BertTokenizer, BertForSequenceClassification, get_linear_schedule_with_warmup
from torch.optim import AdamW
from torch.utils.data import DataLoader, TensorDataset, RandomSampler, SequentialSampler

# 设置临时文件夹避免中文路径问题
import tempfile
temp_dir = tempfile.mkdtemp(suffix='_joblib')
os.environ['JOBLIB_TEMP_FOLDER'] = temp_dir

# 设置随机种子
SEED = 42
np.random.seed(SEED)
random.seed(SEED)
tf.random.set_seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

# 配置参数
DATASET_PATH = 'weibo_senti_100k.csv'
MAX_LEN = 64
VOCAB_SIZE = 10000
EMBED_SIZE = 128

# 创建模型保存目录
os.makedirs('comparison_models', exist_ok=True)
os.makedirs('comparison_results', exist_ok=True)

# -------------------------- 数据加载函数 --------------------------
# 复用现有代码中的函数
def get_file_encoding(file_path):
    """自动检测文件编码"""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)
    encoding_info = detect(raw_data)
    encoding = encoding_info['encoding'] or 'utf-8'
    return encoding

def read_txt_dataset(txt_path, label):
    """读取TXT文件"""
    encoding = get_file_encoding(txt_path)
    try:
        with open(txt_path, 'r', encoding=encoding, errors='ignore') as f:
            texts = [line.strip() for line in f if line.strip()]
    except:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            texts = [line.strip() for line in f if line.strip()]
    return pd.DataFrame({'review': texts, 'label': label})

def merge_txt_to_csv(csv_path, pos_txt_path, neg_txt_path, merged_path):
    """合并CSV和TXT数据"""
    try:
        csv_df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        csv_df = pd.read_csv(csv_path, encoding='gbk')

    pos_txt_df = read_txt_dataset(pos_txt_path, label=1)
    neg_txt_df = read_txt_dataset(neg_txt_path, label=0)
    txt_df = pd.concat([pos_txt_df, neg_txt_df], ignore_index=True)

    merged_df = pd.concat([csv_df[['review', 'label']], txt_df], ignore_index=True)
    merged_df = merged_df.drop_duplicates(subset=['review']).reset_index(drop=True)
    merged_df.to_csv(merged_path, index=False, encoding='utf-8-sig')
    return merged_df

def augment_text(text):
    """文本增强函数"""
    words = text.split()
    if len(words) < 3:
        return text

    synonyms = {
        '好': ['不错', '赞', '棒', '优秀'],
        '坏': ['差', '烂', '糟', '不行'],
        '开心': ['高兴', '开心', '愉快', '喜悦'],
        '生气': ['愤怒', '气愤', '恼火', '不满'],
        '支持': ['赞同', '认可', '力挺', '拥护'],
        '反对': ['抵制', '反对', '不认同', '排斥']
    }
    if random.random() < 0.3:
        for i in range(len(words)):
            if words[i] in synonyms and random.random() < 0.2:
                words[i] = random.choice(synonyms[words[i]])

    if random.random() < 0.3 and len(words) >= 2:
        idx1, idx2 = random.sample(range(len(words)), 2)
        words[idx1], words[idx2] = words[idx2], words[idx1]

    stop_words = ['的', '了', '是', '在', '有', '就', '都', '呢', '啊', '呀']
    if random.random() < 0.2:
        insert_pos = random.randint(0, len(words))
        words.insert(insert_pos, random.choice(stop_words))

    if random.random() < 0.15 and len(words) > 3:
        del words[random.randint(0, len(words)-1)]

    return ' '.join(words)

def load_merged_dataset():
    """加载合并后的数据集"""
    CSV_PATH = 'weibo_senti_100k.csv'
    POS_TXT_PATH = './data/positive_balanced.txt'
    NEG_TXT_PATH = './data/negative_balanced.txt'
    MERGED_PATH = 'merged_dataset.csv'

    if not os.path.exists(MERGED_PATH):
        print("开始合并TXT和CSV数据集...")
        merged_df = merge_txt_to_csv(CSV_PATH, POS_TXT_PATH, NEG_TXT_PATH, MERGED_PATH)
    else:
        merged_df = pd.read_csv(MERGED_PATH, encoding='utf-8-sig')
        print(f"加载合并数据集：{len(merged_df)} 条")

    def clean_text(text):
        text = str(text).strip()
        text = re.sub(r'http\S+|@\w+|#\w+#', '', text)
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text if len(text) > 1 else ''

    merged_df['cleaned_review'] = merged_df['review'].apply(clean_text)
    merged_df = merged_df[merged_df['cleaned_review'] != ''].reset_index(drop=True)

    # 样本平衡
    pos_df = merged_df[merged_df['label'] == 1]
    neg_df = merged_df[merged_df['label'] == 0]
    min_count = min(len(pos_df), len(neg_df))

    if len(pos_df) > min_count:
        pos_df = pos_df.sample(min_count, random_state=SEED)
    else:
        aug_pos = [augment_text(t) for t in pos_df['cleaned_review'].tolist() * (min_count // len(pos_df) + 1)]
        pos_df = pd.concat([pos_df, pd.DataFrame({'cleaned_review': aug_pos[:min_count - len(pos_df)], 'label': 1})])

    if len(neg_df) > min_count:
        neg_df = neg_df.sample(min_count, random_state=SEED)
    else:
        aug_neg = [augment_text(t) for t in neg_df['cleaned_review'].tolist() * (min_count // len(neg_df) + 1)]
        neg_df = pd.concat([neg_df, pd.DataFrame({'cleaned_review': aug_neg[:min_count - len(neg_df)], 'label': 0})])

    return pd.concat([pos_df, neg_df]).sample(frac=1, random_state=SEED).reset_index(drop=True)

# -------------------------- 数据预处理 --------------------------
def prepare_data(max_samples=None):
    """准备数据，返回训练集和测试集（文本和标签）

    参数：
        max_samples: 最大样本数（可选），如果指定，则对数据集进行采样
    """
    print("加载数据集...")
    dataset = load_merged_dataset()
    texts = dataset['cleaned_review'].tolist()
    labels = dataset['label'].astype(int).tolist()

    print(f"数据集大小：{len(texts)}")
    print(f"正样本数：{sum(labels)}，负样本数：{len(labels)-sum(labels)}")

    # 如果指定了最大样本数，进行采样
    if max_samples is not None and len(texts) > max_samples:
        print(f"采样至 {max_samples} 个样本...")
        # 转换为DataFrame以便于采样
        df = pd.DataFrame({'text': texts, 'label': labels})
        # 使用train_test_split进行分层采样
        _, df_sampled = train_test_split(
            df, train_size=max_samples, random_state=SEED, stratify=df['label']
        )
        texts = df_sampled['text'].tolist()
        labels = df_sampled['label'].tolist()
        print(f"采样后数据集大小：{len(texts)}")
        print(f"采样后正样本数：{sum(labels)}，负样本数：{len(labels)-sum(labels)}")

    # 划分训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, random_state=SEED, stratify=labels
    )

    print(f"训练集大小：{len(X_train)}，测试集大小：{len(X_test)}")

    return X_train, X_test, y_train, y_test

def create_tfidf_features(X_train, X_test, max_features=5000):
    """创建TF-IDF特征"""
    print("创建TF-IDF特征...")
    tfidf = TfidfVectorizer(max_features=max_features, ngram_range=(1, 2))
    X_train_tfidf = tfidf.fit_transform(X_train)
    X_test_tfidf = tfidf.transform(X_test)

    # 保存TF-IDF向量化器
    with open('comparison_models/tfidf_vectorizer.pkl', 'wb') as f:
        pickle.dump(tfidf, f)

    return X_train_tfidf, X_test_tfidf, tfidf

def create_sequence_features(X_train, X_test, vocab_size=VOCAB_SIZE, max_len=MAX_LEN):
    """创建序列特征（用于深度学习模型）"""
    print("创建序列特征...")
    tokenizer = Tokenizer(num_words=vocab_size, filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n', lower=True)
    tokenizer.fit_on_texts(X_train)

    X_train_seq = tokenizer.texts_to_sequences(X_train)
    X_test_seq = tokenizer.texts_to_sequences(X_test)

    # 手动填充序列
    def pad_sequences(sequences, maxlen=None, padding='pre', truncating='post', value=0):
        if maxlen is None:
            maxlen = max(len(x) for x in sequences)
        result = np.full((len(sequences), maxlen), value, dtype='int32')
        for i, seq in enumerate(sequences):
            seq_len = len(seq)
            if seq_len == 0:
                continue
            if seq_len > maxlen:
                seq = seq[:maxlen] if truncating == 'post' else seq[-maxlen:]
                seq_len = maxlen
            if padding == 'post':
                result[i, :seq_len] = seq
            else:
                result[i, -seq_len:] = seq
        return result

    X_train_padded = pad_sequences(X_train_seq, maxlen=max_len, padding='pre', truncating='post')
    X_test_padded = pad_sequences(X_test_seq, maxlen=max_len, padding='pre', truncating='post')

    # 保存tokenizer
    with open('comparison_models/tokenizer.pkl', 'wb') as f:
        pickle.dump(tokenizer, f)

    return X_train_padded, X_test_padded, tokenizer

# -------------------------- 评估函数 --------------------------
def evaluate_model(y_true, y_pred, y_pred_proba=None, model_name=""):
    """评估模型性能"""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, average='binary', pos_label=1)
    recall = recall_score(y_true, y_pred, average='binary', pos_label=1)
    f1 = f1_score(y_true, y_pred, average='binary', pos_label=1)
    # F-beta分数
    f2 = fbeta_score(y_true, y_pred, beta=2, average='binary', pos_label=1)  # 更重视召回率
    f0_5 = fbeta_score(y_true, y_pred, beta=0.5, average='binary', pos_label=1)  # 更重视精确率

    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'f2': f2,
        'f0_5': f0_5
    }

    # 计算混淆矩阵及其他衍生指标
    try:
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        # 特异性 (Specificity) = TN / (TN + FP)
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        # 阴性预测值 (Negative Predictive Value) = TN / (TN + FN)
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        # 假阳性率 (False Positive Rate) = FP / (FP + TN)
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        # 假阴性率 (False Negative Rate) = FN / (FN + TP)
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
        # 几何平均数 (Geometric Mean) = sqrt(召回率 * 特异性)
        gmean = np.sqrt(recall * specificity) if recall >= 0 and specificity >= 0 else 0

        metrics['specificity'] = specificity
        metrics['npv'] = npv
        metrics['fpr'] = fpr
        metrics['fnr'] = fnr
        metrics['gmean'] = gmean
    except Exception as e:
        print(f"警告: 计算混淆矩阵衍生指标时出错: {e}")
        metrics['specificity'] = None
        metrics['npv'] = None
        metrics['fpr'] = None
        metrics['fnr'] = None
        metrics['gmean'] = None

    # 计算其他分类指标
    try:
        # 平衡准确率 (Balanced Accuracy)
        balanced_acc = balanced_accuracy_score(y_true, y_pred)
        metrics['balanced_accuracy'] = balanced_acc
    except:
        metrics['balanced_accuracy'] = None

    try:
        # 马修斯相关系数 (Matthews Correlation Coefficient)
        mcc = matthews_corrcoef(y_true, y_pred)
        metrics['mcc'] = mcc
    except:
        metrics['mcc'] = None

    try:
        # 科恩卡帕系数 (Cohen's Kappa)
        kappa = cohen_kappa_score(y_true, y_pred)
        metrics['kappa'] = kappa
    except:
        metrics['kappa'] = None

    # 添加其他分类指标
    try:
        # Jaccard相似系数
        jaccard = jaccard_score(y_true, y_pred, average='binary', pos_label=1)
        metrics['jaccard'] = jaccard
    except:
        metrics['jaccard'] = None

    try:
        # 汉明损失
        hamming = hamming_loss(y_true, y_pred)
        metrics['hamming_loss'] = hamming
    except:
        metrics['hamming_loss'] = None

    try:
        # 零一损失
        zero_one = zero_one_loss(y_true, y_pred)
        metrics['zero_one_loss'] = zero_one
    except:
        metrics['zero_one_loss'] = None

    if y_pred_proba is not None:
        try:
            auc = roc_auc_score(y_true, y_pred_proba)
            metrics['auc'] = auc
        except:
            metrics['auc'] = None
        # 计算MAE、MSE、RMSE、R2、MAPE（预测概率与真实标签之间的误差）
        try:
            # 检查数据类型
            if hasattr(y_true, '__len__') and hasattr(y_pred_proba, '__len__'):
                print(f"DEBUG: y_true type: {type(y_true)}, length: {len(y_true)}")
                print(f"DEBUG: y_pred_proba type: {type(y_pred_proba)}, length: {len(y_pred_proba)}")
                if len(y_true) > 0:
                    print(f"DEBUG: y_true[0] type: {type(y_true[0])}, value: {y_true[0]}")
                if len(y_pred_proba) > 0:
                    print(f"DEBUG: y_pred_proba[0] type: {type(y_pred_proba[0])}, value: {y_pred_proba[0]}")

            # 确保y_pred_proba是浮点数类型
            if hasattr(y_pred_proba, 'dtype') and y_pred_proba.dtype != np.float64 and y_pred_proba.dtype != np.float32:
                y_pred_proba = y_pred_proba.astype(np.float64)
            elif not hasattr(y_pred_proba, 'dtype') and isinstance(y_pred_proba, (list, tuple)):
                # 如果是Python列表或元组，转换为numpy数组
                y_pred_proba = np.array(y_pred_proba, dtype=np.float64)

            mae = mean_absolute_error(y_true, y_pred_proba)
            mse = mean_squared_error(y_true, y_pred_proba)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_true, y_pred_proba)
            # 计算MAPE，处理y_true=0的情况
            try:
                mape = mean_absolute_percentage_error(y_true, y_pred_proba)
            except:
                # 自定义MAPE计算，避免除以零
                epsilon = 1e-10
                mape = np.mean(np.abs((y_true - y_pred_proba) / (np.abs(y_true) + epsilon))) * 100

            metrics['mae'] = mae
            metrics['mse'] = mse
            metrics['rmse'] = rmse
            metrics['r2'] = r2
            metrics['mape'] = mape
        except Exception as e:
            print(f"ERROR calculating regression metrics: {e}")
            print(f"y_true type: {type(y_true)}, y_pred_proba type: {type(y_pred_proba)}")
            if hasattr(y_true, '__len__'):
                print(f"y_true length: {len(y_true)}")
            if hasattr(y_pred_proba, '__len__'):
                print(f"y_pred_proba length: {len(y_pred_proba)}")
            metrics['mae'] = None
            metrics['mse'] = None
            metrics['rmse'] = None
            metrics['r2'] = None
            metrics['mape'] = None

        # 添加基于概率的指标
        try:
            # 对数损失（交叉熵）
            logloss = log_loss(y_true, y_pred_proba)
            metrics['log_loss'] = logloss
        except:
            metrics['log_loss'] = None

        try:
            # Brier分数损失
            brier = brier_score_loss(y_true, y_pred_proba)
            metrics['brier_score'] = brier
        except:
            metrics['brier_score'] = None

        try:
            # 夏普比率（预测概率的均值/标准差，无风险利率设为0）
            mean_return = np.mean(y_pred_proba)
            std_return = np.std(y_pred_proba)
            if std_return > 0:
                sharpe_ratio = mean_return / std_return
            else:
                sharpe_ratio = 0.0  # 标准差为0，夏普比率设为0
            metrics['sharpe_ratio'] = sharpe_ratio
        except:
            metrics['sharpe_ratio'] = None

    # 打印结果
    print(f"\n{model_name} 评估结果:")
    print(f"准确率: {accuracy:.4f}")
    print(f"精确率: {precision:.4f}")
    print(f"召回率: {recall:.4f}")
    print(f"F1分数: {f1:.4f}")
    if 'specificity' in metrics and metrics['specificity'] is not None:
        print(f"特异性: {metrics['specificity']:.4f}")
    if 'npv' in metrics and metrics['npv'] is not None:
        print(f"阴性预测值: {metrics['npv']:.4f}")
    if 'fpr' in metrics and metrics['fpr'] is not None:
        print(f"假阳性率: {metrics['fpr']:.4f}")
    if 'fnr' in metrics and metrics['fnr'] is not None:
        print(f"假阴性率: {metrics['fnr']:.4f}")
    if 'gmean' in metrics and metrics['gmean'] is not None:
        print(f"几何平均数: {metrics['gmean']:.4f}")
    if 'balanced_accuracy' in metrics and metrics['balanced_accuracy'] is not None:
        print(f"平衡准确率: {metrics['balanced_accuracy']:.4f}")
    if 'mcc' in metrics and metrics['mcc'] is not None:
        print(f"马修斯相关系数: {metrics['mcc']:.4f}")
    if 'kappa' in metrics and metrics['kappa'] is not None:
        print(f"科恩卡帕系数: {metrics['kappa']:.4f}")
    if 'auc' in metrics and metrics['auc'] is not None:
        print(f"AUC-ROC: {metrics['auc']:.4f}")
    if 'mae' in metrics and metrics['mae'] is not None:
        print(f"MAE: {metrics['mae']:.4f}")
    if 'mse' in metrics and metrics['mse'] is not None:
        print(f"MSE: {metrics['mse']:.4f}")
    if 'rmse' in metrics and metrics['rmse'] is not None:
        print(f"RMSE: {metrics['rmse']:.4f}")
    if 'r2' in metrics and metrics['r2'] is not None:
        print(f"R2: {metrics['r2']:.4f}")
    if 'mape' in metrics and metrics['mape'] is not None:
        print(f"MAPE: {metrics['mape']:.4f}%")
    # 打印新增指标
    if 'f0_5' in metrics and metrics['f0_5'] is not None:
        print(f"F0.5分数: {metrics['f0_5']:.4f}")
    if 'f2' in metrics and metrics['f2'] is not None:
        print(f"F2分数: {metrics['f2']:.4f}")
    if 'jaccard' in metrics and metrics['jaccard'] is not None:
        print(f"Jaccard系数: {metrics['jaccard']:.4f}")
    if 'hamming_loss' in metrics and metrics['hamming_loss'] is not None:
        print(f"汉明损失: {metrics['hamming_loss']:.4f}")
    if 'zero_one_loss' in metrics and metrics['zero_one_loss'] is not None:
        print(f"零一损失: {metrics['zero_one_loss']:.4f}")
    if 'log_loss' in metrics and metrics['log_loss'] is not None:
        print(f"对数损失: {metrics['log_loss']:.4f}")
    if 'brier_score' in metrics and metrics['brier_score'] is not None:
        print(f"Brier分数: {metrics['brier_score']:.4f}")
    if 'sharpe_ratio' in metrics and metrics['sharpe_ratio'] is not None:
        print(f"夏普比率: {metrics['sharpe_ratio']:.4f}")

    return metrics

def save_results(model_name, metrics, params=None):
    """保存评估结果"""
    results_dir = 'comparison_results'
    os.makedirs(results_dir, exist_ok=True)

    results_file = os.path.join(results_dir, f'{model_name}_results.txt')
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write(f"{model_name} 评估结果\n")
        f.write("=" * 50 + "\n")
        for key, value in metrics.items():
            f.write(f"{key}: {value}\n")

        if params:
            f.write("\n模型参数:\n")
            for key, value in params.items():
                f.write(f"{key}: {value}\n")

    print(f"结果保存至 {results_file}")

# -------------------------- 逻辑回归模型 --------------------------
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV

def train_logistic_regression(X_train, X_test, y_train, y_test):
    """训练逻辑回归模型"""
    print("\n" + "="*50)
    print("训练逻辑回归模型...")

    # 简化参数网格，避免过长的训练时间
    param_grid = {
        'C': [0.1, 1, 10],
        'penalty': ['l2'],  # 使用L2正则化
        'solver': ['lbfgs']  # 适合小到中型数据集
    }

    # 使用GridSearchCV进行参数调优，设置n_jobs=1避免并行问题
    lr = LogisticRegression(random_state=SEED, max_iter=1000)
    grid_search = GridSearchCV(lr, param_grid, cv=3, scoring='f1', n_jobs=1, verbose=1)
    grid_search.fit(X_train, y_train)

    # 最佳模型
    best_lr = grid_search.best_estimator_
    print(f"最佳参数: {grid_search.best_params_}")
    print(f"最佳交叉验证F1分数: {grid_search.best_score_:.4f}")

    # 在测试集上评估
    y_pred = best_lr.predict(X_test)
    y_pred_proba = best_lr.predict_proba(X_test)[:, 1]

    metrics = evaluate_model(y_test, y_pred, y_pred_proba, "Logistic Regression")

    # 保存模型
    model_path = 'comparison_models/logistic_regression_model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(best_lr, f)
    print(f"逻辑回归模型保存至 {model_path}")

    # 保存结果
    save_results('Logistic_Regression', metrics, grid_search.best_params_)

    return best_lr, metrics

# -------------------------- BERT模型 --------------------------
def train_bert(X_train, X_test, y_train, y_test, max_len=MAX_LEN, batch_size=16, epochs=3):
    """训练BERT模型"""
    print("\n" + "="*50)
    print("训练BERT模型...")

    # 检查GPU是否可用
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"使用设备: {device}")

    # 加载预训练模型和tokenizer
    model_name = 'bert-base-chinese'
    tokenizer = BertTokenizer.from_pretrained(model_name)
    model = BertForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
        output_attentions=False,
        output_hidden_states=False
    )
    model.to(device)

    # 对文本进行tokenization
    def tokenize_texts(texts):
        return tokenizer(
            texts,
            max_length=max_len,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

    train_encodings = tokenize_texts(X_train)
    test_encodings = tokenize_texts(X_test)

    # 创建PyTorch数据集
    class SentimentDataset(torch.utils.data.Dataset):
        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels

        def __getitem__(self, idx):
            item = {key: val[idx] for key, val in self.encodings.items()}
            item['labels'] = torch.tensor(self.labels[idx], dtype=torch.long)
            return item

        def __len__(self):
            return len(self.labels)

    train_dataset = SentimentDataset(train_encodings, y_train)
    test_dataset = SentimentDataset(test_encodings, y_test)

    # 创建DataLoader
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    # 优化器和学习率调度器
    optimizer = AdamW(model.parameters(), lr=2e-5)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(0.1 * total_steps),
        num_training_steps=total_steps
    )

    # 训练循环
    model.train()
    for epoch in range(epochs):
        print(f"\nEpoch {epoch + 1}/{epochs}")
        total_loss = 0
        for batch in train_loader:
            # 将数据移动到设备
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            optimizer.zero_grad()
            outputs = model(input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            total_loss += loss.item()

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

        avg_loss = total_loss / len(train_loader)
        print(f"训练损失: {avg_loss:.4f}")

    # 评估模型
    model.eval()
    all_preds = []
    all_labels = []
    all_probs = []

    with torch.no_grad():
        for batch in test_loader:
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['labels'].to(device)

            outputs = model(input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1)
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs[:, 1].cpu().numpy())  # 正类的概率

    # 计算指标
    metrics = evaluate_model(all_labels, all_preds, all_probs, "BERT")

    # 保存模型
    model_path = 'comparison_models/bert_model'
    model.save_pretrained(model_path)
    tokenizer.save_pretrained(model_path)
    print(f"BERT模型保存至 {model_path}")

    # 保存结果
    save_results('BERT', metrics, {'epochs': epochs, 'batch_size': batch_size})

    return model, metrics

# -------------------------- 朴素贝叶斯模型 --------------------------
from sklearn.naive_bayes import MultinomialNB

def train_naive_bayes(X_train, X_test, y_train, y_test):
    """训练朴素贝叶斯模型"""
    print("\n" + "="*50)
    print("训练朴素贝叶斯模型...")

    # 训练模型
    nb = MultinomialNB()
    nb.fit(X_train, y_train)

    # 在测试集上评估
    y_pred = nb.predict(X_test)
    y_pred_proba = nb.predict_proba(X_test)[:, 1]

    metrics = evaluate_model(y_test, y_pred, y_pred_proba, "Naive Bayes")

    # 保存模型
    model_path = 'comparison_models/naive_bayes_model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(nb, f)
    print(f"朴素贝叶斯模型保存至 {model_path}")

    # 保存结果
    save_results('Naive_Bayes', metrics, {})

    return nb, metrics

# -------------------------- LSTM模型 --------------------------
def train_lstm(X_train_seq, X_test_seq, y_train, y_test, vocab_size=VOCAB_SIZE, embed_size=EMBED_SIZE, max_len=MAX_LEN):
    """训练LSTM模型"""
    print("\n" + "="*50)
    print("训练LSTM模型...")
    # 确保标签为NumPy数组以兼容Keras
    y_train = np.array(y_train)
    y_test = np.array(y_test)

    # 构建模型
    model = Sequential()
    model.add(Embedding(input_dim=vocab_size+1, output_dim=embed_size, input_length=max_len))
    model.add(Bidirectional(LSTM(64, return_sequences=True)))
    model.add(Dropout(0.5))
    model.add(Bidirectional(LSTM(32)))
    model.add(Dropout(0.5))
    model.add(Dense(16, activation='relu'))
    model.add(Dense(1, activation='sigmoid'))

    model.compile(
        loss='binary_crossentropy',
        optimizer=Adam(learning_rate=0.001),
        metrics=['accuracy']
    )

    # 回调函数
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2)
    ]

    # 训练模型
    history = model.fit(
        X_train_seq, y_train,
        validation_split=0.1,
        epochs=10,
        batch_size=64,
        callbacks=callbacks,
        verbose=1
    )

    # 在测试集上评估
    y_pred_proba = model.predict(X_test_seq, verbose=0).flatten()
    y_pred = (y_pred_proba > 0.5).astype(int)

    metrics = evaluate_model(y_test, y_pred, y_pred_proba, "LSTM")

    # 保存模型
    model_path = 'comparison_models/lstm_model.h5'
    model.save(model_path)
    print(f"LSTM模型保存至 {model_path}")

    # 保存结果
    save_results('LSTM', metrics, {})

    return model, metrics

# -------------------------- CNN模型（现有模型适配） --------------------------
def train_cnn(X_train_seq, X_test_seq, y_train, y_test, vocab_size=VOCAB_SIZE, embed_size=EMBED_SIZE, max_len=MAX_LEN):
    """训练CNN模型（基于现有架构）"""
    print("\n" + "="*50)
    print("训练CNN模型...")
    # 确保标签为NumPy数组以兼容Keras
    y_train = np.array(y_train)
    y_test = np.array(y_test)

    model = Sequential()
    model.add(Embedding(
        input_dim=vocab_size + 1,
        output_dim=embed_size,
        input_length=max_len,
        trainable=True
    ))
    model.add(Conv1D(filters=32, kernel_size=3, padding='same', activation='gelu'))
    model.add(MaxPool1D(pool_size=2))
    model.add(Dropout(0.6))
    model.add(Conv1D(filters=16, kernel_size=3, padding='same', activation='gelu'))
    model.add(MaxPool1D(pool_size=2))
    model.add(Dropout(0.6))
    model.add(Flatten())
    model.add(Dense(16, activation='gelu', kernel_regularizer=l2(0.001)))
    model.add(BatchNormalization())
    model.add(Dense(1, activation='sigmoid'))

    optimizer = Adam(learning_rate=0.0005, decay=1e-6)
    model.compile(loss='binary_crossentropy', optimizer=optimizer, metrics=['accuracy'])

    # 回调函数
    callbacks = [
        EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2)
    ]

    # 训练模型
    history = model.fit(
        X_train_seq, y_train,
        validation_split=0.1,
        epochs=20,
        batch_size=64,
        callbacks=callbacks,
        verbose=1
    )

    # 在测试集上评估
    y_pred_proba = model.predict(X_test_seq, verbose=0).flatten()
    y_pred = (y_pred_proba > 0.5).astype(int)

    metrics = evaluate_model(y_test, y_pred, y_pred_proba, "CNN")

    # 保存模型
    model_path = 'comparison_models/cnn_model.h5'
    model.save(model_path)
    print(f"CNN模型保存至 {model_path}")

    # 保存结果
    save_results('CNN', metrics, {})

    return model, metrics

def run_all_experiments(max_samples=None):
    """运行所有对比实验

    参数：
        max_samples: 最大样本数（可选），如果指定，则对数据集进行采样
    """
    print("="*60)
    print("开始情感分析模型对比实验")
    print("="*60)

    # 1. 准备数据
    print(f"最大样本数限制: {max_samples if max_samples else '无'}")
    X_train, X_test, y_train, y_test = prepare_data(max_samples=max_samples)

    # 2. 创建特征
    print("\n创建特征...")
    # TF-IDF特征（用于逻辑回归和朴素贝叶斯）
    X_train_tfidf, X_test_tfidf, tfidf = create_tfidf_features(X_train, X_test, max_features=5000)
    # 序列特征（用于深度学习模型）
    X_train_seq, X_test_seq, tokenizer = create_sequence_features(X_train, X_test)

    results = {}

    # 3. 训练和评估朴素贝叶斯模型（快速基准）
    print("\n" + "="*60)
    print("1. 朴素贝叶斯模型")
    nb_model, nb_metrics = train_naive_bayes(X_train_tfidf, X_test_tfidf, y_train, y_test)
    results['Naive Bayes'] = nb_metrics

    # 4. 训练和评估逻辑回归模型
    print("\n" + "="*60)
    print("2. 逻辑回归模型")
    lr_model, lr_metrics = train_logistic_regression(X_train_tfidf, X_test_tfidf, y_train, y_test)
    results['Logistic Regression'] = lr_metrics

    # 5. 训练和评估CNN模型
    print("\n" + "="*60)
    print("3. CNN模型")
    cnn_model, cnn_metrics = train_cnn(X_train_seq, X_test_seq, y_train, y_test)
    results['CNN'] = cnn_metrics

    # 6. 训练和评估LSTM模型
    print("\n" + "="*60)
    print("4. LSTM模型")
    lstm_model, lstm_metrics = train_lstm(X_train_seq, X_test_seq, y_train, y_test)
    results['LSTM'] = lstm_metrics

    # 7. 训练和评估BERT模型（可选，耗时较长）
    print("\n" + "="*60)
    print("5. BERT模型（Transformer）")
    print("注意：BERT模型训练可能需要较长时间...")

    # 询问是否训练BERT模型
    user_input = input("是否训练BERT模型？(y/n): ")
    if user_input.lower() == 'y':
        bert_model, bert_metrics = train_bert(X_train, X_test, y_train, y_test, max_len=MAX_LEN, epochs=2)
        results['BERT'] = bert_metrics
    else:
        print("跳过BERT模型训练。")
        results['BERT'] = None

    # 8. 生成对比报告
    total_samples = len(X_train) + len(X_test)
    generate_comparison_report(results, total_samples=total_samples)

    print("\n" + "="*60)
    print("所有实验完成！")
    print("="*60)

def generate_comparison_report(results, total_samples=None):
    """生成对比实验报告

    参数：
        results: 模型评估结果字典
        total_samples: 总样本数（可选）
    """
    print("\n" + "="*60)
    print("模型性能对比报告")
    print("="*60)

    # 过滤掉None结果
    valid_results = {k: v for k, v in results.items() if v is not None}

    # 创建对比表格
    import pandas as pd
    df = pd.DataFrame(valid_results).T
    # 按顺序排列，包含新指标
    desired_cols = ['accuracy', 'precision', 'recall', 'f1', 'auc', 'mae', 'mse']
    existing_cols = [col for col in desired_cols if col in df.columns]
    df = df[existing_cols]

    # 打印表格
    print("\n性能指标对比:")
    print(df.round(4))

    # 保存为CSV
    report_path = 'comparison_results/model_comparison.csv'
    df.to_csv(report_path, encoding='utf-8-sig')
    print(f"\n对比结果已保存至: {report_path}")

    # 生成简单分析
    print("\n分析:")
    for metric in df.columns:
        if metric in ['mae', 'mse']:
            # 误差指标，值越小越好
            best_model = df[metric].idxmin()
            best_score = df[metric].min()
            print(f"- 最佳{metric}模型: {best_model} ({best_score:.4f}) (误差最低)")
        else:
            # 分类指标，值越大越好
            best_model = df[metric].idxmax()
            best_score = df[metric].max()
            print(f"- 最佳{metric}模型: {best_model} ({best_score:.4f})")

    # 保存详细报告
    report_file = 'comparison_results/detailed_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 情感分析模型对比实验报告\n\n")
        f.write("## 实验概述\n")
        f.write(f"- 数据集: weibo_senti_100k.csv + 平衡TXT数据\n")
        if total_samples is not None:
            f.write(f"- 总样本数: {total_samples}\n")
        else:
            f.write(f"- 总样本数: 未指定（使用全部可用数据）\n")
        f.write(f"- 训练集/测试集比例: 80%/20%\n")
        f.write(f"- 随机种子: {SEED}\n\n")

        f.write("## 模型性能对比\n\n")
        f.write(df.to_markdown() + "\n\n")

        f.write("## 结论\n")
        f.write("根据以上实验结果，可以得出以下结论:\n")
        for metric in df.columns:
            if metric in ['mae', 'mse']:
                # 误差指标，值越小越好
                best_model = df[metric].idxmin()
                best_score = df[metric].min()
                f.write(f"1. 在{metric}指标上，{best_model}表现最佳，误差最低，达到{best_score:.4f}。\n")
            else:
                # 分类指标，值越大越好
                best_model = df[metric].idxmax()
                best_score = df[metric].max()
                f.write(f"1. 在{metric}指标上，{best_model}表现最佳，达到{best_score:.4f}。\n")

    print(f"详细报告已保存至: {report_file}")

if __name__ == '__main__':
    # 运行所有实验
    run_all_experiments()