import os
import gc
import random
import pickle
import numpy as np
import pandas as pd
import re  # 新增正则表达式库用于文本清洗
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, accuracy_score
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.layers import Embedding, Dense, Conv1D, MaxPool1D, Flatten, Dropout, BatchNormalization
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.callbacks import Callback, EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2
from tensorflow.keras.activations import gelu  # 新增更适合文本的激活函数

np.random.seed(42)
os.makedirs('model', exist_ok=True)

# -------------------------- 配置参数 --------------------------
# 核心修改：指定微博情感数据集路径
DATASET_PATH = 'weibo_senti_100k.csv'  # 确保该文件与代码在同一目录或填写绝对路径
MAX_LEN = 64  # 根据微博文本长度调整（可适当增大至128）
embed_size = 128
vocab_size = 10000  # 微博词汇量更大，适当增大词汇表
MODEL_SAVE_PATH = './model/weibo_model.h5'
TOKENIZER_SAVE_PATH = 'weibo_tokenizer.pkl'
CSV_INPUT_PATH = 'stock_comments.csv'  # 待分类的评论文件
CSV_OUTPUT_PATH = 'stock_comments_with_sentiment.csv'


# -------------------------- 1. 手动实现pad_sequences --------------------------
def pad_sequences(sequences, maxlen=None, dtype='int32', padding='pre', truncating='post', value=0.):
    # 修改padding为'pre'（文本分类更优）
    if maxlen is None:
        maxlen = max(len(x) for x in sequences)
    result = np.full((len(sequences), maxlen), value, dtype=dtype)
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
#处理txt和csv的不同编码
from chardet import detect  # 需要先安装：pip install chardet

def get_file_encoding(file_path):
    """自动检测文件编码，返回最可能的编码格式"""
    with open(file_path, 'rb') as f:
        raw_data = f.read(10000)  # 读取前10KB用于检测
    encoding_info = detect(raw_data)
    encoding = encoding_info['encoding'] or 'utf-8'  # 编码为空时默认UTF-8
    print(f"检测到 {os.path.basename(file_path)} 编码：{encoding}（置信度：{encoding_info['confidence']:.2f}）")
    return encoding


def read_txt_dataset(txt_path, label):
    """读取TXT文件，按正确编码解析，返回与CSV结构一致的DataFrame"""
    encoding = get_file_encoding(txt_path)
    try:
        # 用检测到的编码读取，忽略少量错误字符
        with open(txt_path, 'r', encoding=encoding, errors='ignore') as f:
            texts = [line.strip() for line in f if line.strip()]  # 过滤空行
    except:
        # 失败时降级为UTF-8读取
        print(f"编码 {encoding} 读取失败，尝试UTF-8...")
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            texts = [line.strip() for line in f if line.strip()]

    # 返回DataFrame（与CSV列名一致：'review'存文本，'label'存标签）
    return pd.DataFrame({'review': texts, 'label': label})

# -------------------------- 2. 金融专业术语同义词词典 --------------------------
FINANCIAL_SYNONYMS = {
    # 价格变动
    '上涨': ['攀升', '走高', '上扬', '拉升', '暴涨', '飙升', '大涨'],
    '下跌': ['下滑', '走低', '下挫', '回落', '暴跌', '狂泻', '大跌'],
    '平稳': ['持平', '横盘', '震荡', '波动', '盘整'],
    # 盈利相关
    '盈利': ['收益', '获利', '赚钱', '盈余', '利润'],
    '亏损': ['赔钱', '亏本', '蚀本', '失利', '损失'],
    '增长': ['增加', '上升', '提高', '扩大', '攀升'],
    '减少': ['下降', '降低', '缩小', '缩减', '下滑'],
    # 市场状态
    '牛市': ['多头市场', '上涨行情', '乐观市场'],
    '熊市': ['空头市场', '下跌行情', '悲观市场'],
    '震荡': ['波动', '起伏', '摇摆', '反复'],
    # 投资动作
    '买入': ['买进', '购入', '建仓', '加仓'],
    '卖出': ['卖出', '抛售', '减持', '清仓'],
    '持有': ['持有', '持仓', '保留', '继续持有'],
    # 评价词汇
    '看好': ['乐观', '积极', '正面', '有信心'],
    '看空': ['悲观', '消极', '负面', '不看好'],
    '推荐': ['建议买入', '推荐持有', '强烈推荐'],
    '回避': ['建议卖出', '回避风险', '谨慎对待'],
    # 财务指标
    '营收': ['营业收入', '销售额', '销售收入'],
    '利润': ['净利润', '盈利', '净收益'],
    '资产': ['总资产', '资产规模', '财产'],
    '负债': ['总负债', '债务', '欠款'],
    # 风险相关
    '风险': ['危险', '不确定性', '隐患', '波动风险'],
    '机会': ['机遇', '时机', '突破口', '潜在收益'],
    '稳定': ['稳健', '牢固', '可靠', '平稳'],
    '波动': ['起伏', '震荡', '变化', '不稳定'],
    # 政策影响
    '利好': ['积极影响', '正面消息', '促进因素'],
    '利空': ['消极影响', '负面消息', '抑制因素'],
    '政策': ['政策措施', '政府调控', '监管政策'],
    # 经济周期
    '复苏': ['回升', '回暖', '恢复', '好转'],
    '衰退': ['萎缩', '下滑', '低迷', '不景气'],
    '繁荣': ['兴旺', '昌盛', '鼎盛', '景气']
}

def normalize_financial_terms(text):
    """将金融术语的不同表达统一为标准术语"""
    # 收集所有同义词-标准术语对，按同义词长度降序排序（避免部分替换）
    pairs = []
    for standard_term, synonyms in FINANCIAL_SYNONYMS.items():
        for synonym in synonyms:
            pairs.append((synonym, standard_term))
    # 按同义词长度降序排序
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    # 依次替换
    for synonym, standard_term in pairs:
        if synonym in text:
            text = text.replace(synonym, standard_term)
    return text

def replace_financial_synonyms_randomly(text):
    """随机将金融术语替换为其同义词，用于数据增强"""
    # 收集所有可能的替换项（标准术语和同义词），按长度降序排序
    replacements = []
    for standard_term, synonyms in FINANCIAL_SYNONYMS.items():
        # 标准术语可以替换为同义词
        replacements.append((standard_term, synonyms))
        # 每个同义词可以替换为其他同义词或标准术语
        for synonym in synonyms:
            replacements.append((synonym, [standard_term] + [s for s in synonyms if s != synonym]))
    # 按术语长度降序排序，避免部分替换
    replacements.sort(key=lambda x: len(x[0]), reverse=True)

    # 遍历每个术语
    for term, candidate_list in replacements:
        if term in text and random.random() < 0.2:
            if candidate_list:
                new_term = random.choice(candidate_list)
                text = text.replace(term, new_term)
                # 替换后跳出当前循环，避免多次替换同一术语
                break
    return text

# -------------------------- 2. 文本增强函数（适配微博文本） --------------------------
def augment_text(text):
    """针对微博文本的增强：同义词替换+随机插入/删除"""
    words = text.split()
    if len(words) < 3:
        return text

    # 1. 金融专业术语随机替换（增强数据多样性）
    if random.random() < 0.3:
        text = replace_financial_synonyms_randomly(text)
        words = text.split()  # 重新分词，因为文本可能已改变

    # 2. 微博常用词同义词替换
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

    # 3. 随机交换词序
    if random.random() < 0.3 and len(words) >= 2:
        idx1, idx2 = random.sample(range(len(words)), 2)
        words[idx1], words[idx2] = words[idx2], words[idx1]

    # 4. 随机插入停用词
    stop_words = ['的', '了', '是', '在', '有', '就', '都', '呢', '啊', '呀']
    if random.random() < 0.2:
        insert_pos = random.randint(0, len(words))
        words.insert(insert_pos, random.choice(stop_words))

    # 5. 随机删除词
    if random.random() < 0.15 and len(words) > 3:
        del words[random.randint(0, len(words)-1)]

    return ' '.join(words)

#整合两个数据集
def merge_txt_to_csv(csv_path, pos_txt_path, neg_txt_path, merged_path):
    """合并CSV和TXT数据，去重后保存为UTF-8-SIG格式（无乱码）"""
    # 读取原有CSV
    try:
        csv_df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        csv_df = pd.read_csv(csv_path, encoding='gbk')
    print(f"原有CSV数据：{len(csv_df)} 条")

    # 读取TXT（积极=1，消极=0）
    pos_txt_df = read_txt_dataset(pos_txt_path, label=1)
    neg_txt_df = read_txt_dataset(neg_txt_path, label=0)
    txt_df = pd.concat([pos_txt_df, neg_txt_df], ignore_index=True)
    print(f"TXT数据总量：{len(txt_df)} 条")

    # 合并并去重（避免重复样本）
    merged_df = pd.concat([csv_df[['review', 'label']], txt_df], ignore_index=True)
    merged_df = merged_df.drop_duplicates(subset=['review']).reset_index(drop=True)

    # 统一保存为UTF-8-SIG（兼容所有工具）
    merged_df.to_csv(merged_path, index=False, encoding='utf-8-sig')
    print(f"合并完成！总数据：{len(merged_df)} 条，保存至 {merged_path}")
    return merged_df


def load_merged_dataset():
    """加载合并后的数据集（替换原有的load_weibo_dataset函数）"""
    # 配置路径（根据你的实际路径修改）
    CSV_PATH = 'weibo_senti_100k.csv'
    POS_TXT_PATH = './data/positive_balanced.txt'
    NEG_TXT_PATH = './data/negative_balanced.txt'
    MERGED_PATH = 'merged_dataset.csv'  # 合并后的数据

    # 若未合并则自动合并
    if not os.path.exists(MERGED_PATH):
        print("开始合并TXT和CSV数据集...")
        merged_df = merge_txt_to_csv(CSV_PATH, POS_TXT_PATH, NEG_TXT_PATH, MERGED_PATH)
    else:
        merged_df = pd.read_csv(MERGED_PATH, encoding='utf-8-sig')
        print(f"加载合并数据集：{len(merged_df)} 条")

    # 以下是原有的文本清洗和样本平衡逻辑（保持不变）
    def clean_text(text):
        text = str(text).strip()
        text = re.sub(r'http\S+|@\w+|#\w+#', '', text)  # 去除链接、@、话题
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text if len(text) > 1 else ''

    merged_df['cleaned_review'] = merged_df['review'].apply(clean_text)
    merged_df['cleaned_review'] = merged_df['cleaned_review'].apply(normalize_financial_terms)
    merged_df = merged_df[merged_df['cleaned_review'] != ''].reset_index(drop=True)

    # 样本平衡（保持原有逻辑）
    pos_df = merged_df[merged_df['label'] == 1]
    neg_df = merged_df[merged_df['label'] == 0]
    min_count = min(len(pos_df), len(neg_df))

    # 截断或增强样本（保持原有逻辑）
    if len(pos_df) > min_count:
        pos_df = pos_df.sample(min_count, random_state=42)
    else:
        aug_pos = [augment_text(t) for t in pos_df['cleaned_review'].tolist() * (min_count // len(pos_df) + 1)]
        pos_df = pd.concat([pos_df, pd.DataFrame({'cleaned_review': aug_pos[:min_count - len(pos_df)], 'label': 1})])

    if len(neg_df) > min_count:
        neg_df = neg_df.sample(min_count, random_state=42)
    else:
        aug_neg = [augment_text(t) for t in neg_df['cleaned_review'].tolist() * (min_count // len(neg_df) + 1)]
        neg_df = pd.concat([neg_df, pd.DataFrame({'cleaned_review': aug_neg[:min_count - len(neg_df)], 'label': 0})])

    return pd.concat([pos_df, neg_df]).sample(frac=1, random_state=42).reset_index(drop=True)

# -------------------------- 3. 数据加载与预处理（核心修改） --------------------------
def load_weibo_dataset():
    """加载微博情感数据集（label列和review列）"""
    try:
        # 读取CSV，指定编码（解决中文乱码）
        df = pd.read_csv(DATASET_PATH, encoding='utf-8-sig')
        print(f"原始数据集规模：{len(df)} 条")
    except UnicodeDecodeError:
        # 尝试其他编码
        df = pd.read_csv(DATASET_PATH, encoding='gbk')
        print(f"使用GBK编码读取，数据集规模：{len(df)} 条")
    except Exception as e:
        print(f"读取数据集失败：{e}")
        exit()

    # 检查必要的列是否存在
    if 'label' not in df.columns or 'review' not in df.columns:
        print("数据集必须包含'label'列（标签）和'review'列（评论内容）")
        exit()

    # 文本清洗：去除特殊字符和冗余内容
    def clean_text(text):
        text = str(text).strip()
        text = re.sub(r'http\S+', '', text)  # 去除URL
        text = re.sub(r'@\w+', '', text)  # 去除@提及
        text = re.sub(r'#\w+#', '', text)  # 去除话题标签
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)  # 保留有效字符
        text = re.sub(r'\s+', ' ', text).strip()  # 合并空格
        return text if len(text) > 1 else ''  # 过滤过短文本

    # 应用清洗并过滤空文本
    df['cleaned_review'] = df['review'].apply(clean_text)
    df['cleaned_review'] = df['cleaned_review'].apply(normalize_financial_terms)
    df = df[df['cleaned_review'] != ''].reset_index(drop=True)
    print(f"清洗后数据集规模：{len(df)} 条")

    # 检查标签分布
    label_counts = df['label'].value_counts()
    print(f"标签分布：积极（1）{label_counts.get(1, 0)} 条，消极（0）{label_counts.get(0, 0)} 条")

    # 数据增强：仅对较少类别的样本进行增强，平衡数据
    pos_df = df[df['label'] == 1]
    neg_df = df[df['label'] == 0]
    min_count = min(len(pos_df), len(neg_df))

    # 对多的类别截断，少的类别增强
    if len(pos_df) > min_count:
        pos_df = pos_df.sample(min_count, random_state=42)
    else:
        # 增强积极样本
        aug_pos = [augment_text(text) for text in pos_df['cleaned_review'].tolist()*(min_count//len(pos_df) + 1)]
        pos_df = pd.concat([pos_df, pd.DataFrame({
            'cleaned_review': aug_pos[:min_count - len(pos_df)],
            'label': 1
        })])

    if len(neg_df) > min_count:
        neg_df = neg_df.sample(min_count, random_state=42)
    else:
        # 增强消极样本
        aug_neg = [augment_text(text) for text in neg_df['cleaned_review'].tolist()*(min_count//len(neg_df) + 1)]
        neg_df = pd.concat([neg_df, pd.DataFrame({
            'cleaned_review': aug_neg[:min_count - len(neg_df)],
            'label': 0
        })])

    # 合并并打乱顺序
    dataset = pd.concat([pos_df, neg_df]).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"平衡后数据集规模：{len(dataset)} 条（积极{len(pos_df)} + 消极{len(neg_df)}）")
    return dataset[['cleaned_review', 'label']]  # 返回清洗后的文本和标签


# -------------------------- 4. 评估指标回调 --------------------------
class Metrics(Callback):
    def __init__(self, val_X, val_y):
        super(Metrics, self).__init__()
        self.val_X = val_X
        self.val_y = val_y

    def on_train_begin(self, logs={}):
        self.val_f1s = []
        self.val_precisions = []
        self.val_recalls = []

    def on_epoch_end(self, epoch, logs={}):
        val_predict = (np.asarray(self.model.predict(self.val_X, verbose=0))).round()
        _val_f1 = f1_score(self.val_y, val_predict, average='binary', pos_label=1)
        _val_precision = precision_score(self.val_y, val_predict, average='binary', pos_label=1)
        _val_recall = recall_score(self.val_y, val_predict, average='binary', pos_label=1)

        self.val_f1s.append(_val_f1)
        self.val_precisions.append(_val_precision)
        self.val_recalls.append(_val_recall)

        print(f"Epoch {epoch + 1} - 验证集F1:{_val_f1:.4f}，精确率:{_val_precision:.4f}，召回率:{_val_recall:.4f}")
        logs['val_f1'] = _val_f1
        return


# -------------------------- 5. 模型训练（优化抗过拟合） --------------------------
def train_model(X_train_padded, X_val_padded, y_train, y_val, tokenizer):
    model = Sequential()
    model.add(Embedding(
        input_dim=vocab_size + 1,
        output_dim=embed_size,
        input_length=MAX_LEN,
        trainable=True
    ))
    # 优化卷积层结构
    model.add(Conv1D(filters=32, kernel_size=3, padding='same', activation=gelu))  # 使用gelu激活
    model.add(MaxPool1D(pool_size=2))
    model.add(Dropout(0.6))
    model.add(Conv1D(filters=16, kernel_size=3, padding='same', activation=gelu))
    model.add(MaxPool1D(pool_size=2))
    model.add(Dropout(0.6))
    model.add(Flatten())
    model.add(Dense(16, activation=gelu, kernel_regularizer=l2(0.001)))  # 增加L2正则
    model.add(BatchNormalization())
    model.add(Dense(1, activation='sigmoid'))

    optimizer = Adam(learning_rate=0.0005, decay=1e-6)  # 降低学习率
    model.compile(loss='binary_crossentropy', optimizer=optimizer, metrics=['accuracy'])
    model.summary()

    # 回调函数
    metrics = Metrics(X_val_padded, y_val)
    early_stopping = EarlyStopping(
        monitor='val_f1', mode='max', patience=5, min_delta=0.001, restore_best_weights=True
    )
    model_checkpoint = ModelCheckpoint(
        MODEL_SAVE_PATH, save_best_only=True, monitor='val_f1', mode='max'
    )
    # 学习率调度器
    reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2, min_lr=1e-6)

    model.fit(
        X_train_padded, y_train,
        batch_size=64,
        epochs=30,
        validation_data=(X_val_padded, y_val),
        callbacks=[metrics, early_stopping, model_checkpoint, reduce_lr]
    )

    # 保存Tokenizer
    with open(TOKENIZER_SAVE_PATH, 'wb') as f:
        pickle.dump(tokenizer, f)
    print(f"Tokenizer保存至：{TOKENIZER_SAVE_PATH}")
    print(f"最优模型保存至：{MODEL_SAVE_PATH}")
    return model


# -------------------------- 6. CSV评论分类 --------------------------
def classify_csv_comments(threshold=0.4):
    try:
        with open(TOKENIZER_SAVE_PATH, 'rb') as f:
            tokenizer = pickle.load(f)
        model = load_model(MODEL_SAVE_PATH)
        print("模型和Tokenizer加载成功")
    except Exception as e:
        print(f"加载失败：{e}")
        return

    try:
        df = pd.read_csv(CSV_INPUT_PATH, encoding='utf-8-sig')
        if 'title' not in df.columns:
            print("CSV缺少'title'列！")
            return
        # 复用微博文本清洗逻辑
        def clean_text(text):
            text = str(text).strip()
            text = re.sub(r'http\S+', '', text)
            text = re.sub(r'@\w+', '', text)
            text = re.sub(r'#\w+#', '', text)
            text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        df['cleaned_text'] = df['title'].apply(clean_text)
        df['cleaned_text'] = df['cleaned_text'].apply(normalize_financial_terms)

        # 编码预测
        seqs = tokenizer.texts_to_sequences(df['cleaned_text'])
        padded_seqs = pad_sequences(seqs, maxlen=MAX_LEN, padding='pre', truncating='post')
        print(f"使用分类阈值: {threshold} (默认0.5)")
        preds = model.predict(padded_seqs, verbose=1)
        sentiment = (preds > threshold).astype(int).flatten()

        # 保存结果
        df['sentiment'] = ['积极' if p == 1 else '消极' for p in sentiment]
        df['positive_prob'] = preds.round(4).flatten()
        df['negative_prob'] = (1 - preds).round(4).flatten()
        df.to_csv(CSV_OUTPUT_PATH, index=False, encoding='utf-8-sig')

        # 统计结果
        pos_cnt = len(df[df['sentiment'] == '积极'])
        neg_cnt = len(df[df['sentiment'] == '消极'])
        total_cnt = len(df)
        print(f"\n分类结果：总评论{total_cnt}条，积极{pos_cnt}条（{pos_cnt/total_cnt:.2%}），消极{neg_cnt}条（{neg_cnt/total_cnt:.2%}）")
        print(f"结果保存至：{CSV_OUTPUT_PATH}")
        print(df[['title', 'positive_prob', 'negative_prob', 'sentiment']].head(10))
    except Exception as e:
        print(f"CSV分类失败：{e}")


def analyze_borderline_cases(threshold=0.4, margin=0.1):
    """
    分析预测概率接近阈值的样本（边界样本）
    这些样本最容易误判，需要特别关注

    :param threshold: 分类阈值
    :param margin: 边界范围，如0.1表示分析[threshold-0.1, threshold+0.1]的样本
    """
    try:
        df = pd.read_csv(CSV_OUTPUT_PATH, encoding='utf-8-sig')

        if 'positive_prob' not in df.columns:
            print("错误：CSV文件中缺少'positive_prob'列")
            return

        # 计算与阈值的距离
        df['prob_diff'] = abs(df['positive_prob'] - threshold)

        # 筛选边界样本
        borderline_df = df[df['prob_diff'] <= margin].copy()
        borderline_df = borderline_df.sort_values('prob_diff')

        total_samples = len(df)
        borderline_count = len(borderline_df)

        print(f"\n=== 边界样本分析 ===")
        print(f"分类阈值: {threshold}")
        print(f"边界范围: ±{margin}")
        print(f"总样本数: {total_samples}")
        print(f"边界样本数: {borderline_count} ({borderline_count/total_samples:.1%})")

        if borderline_count > 0:
            # 统计边界样本的情感分布
            borderline_sentiment = borderline_df['sentiment'].value_counts()
            print(f"\n边界样本情感分布:")
            for sentiment, count in borderline_sentiment.items():
                print(f"  {sentiment}: {count}条 ({count/borderline_count:.1%})")

            # 显示最接近阈值的样本
            print(f"\n最接近阈值的样本（前10条）:")
            for i, row in borderline_df.head(10).iterrows():
                sentiment = row['sentiment']
                prob = row['positive_prob']
                diff = row['prob_diff']
                title_preview = row['title'][:60] + "..." if len(row['title']) > 60 else row['title']
                print(f"  [{sentiment}] 概率:{prob:.4f} (距阈值:{diff:.4f}) - {title_preview}")

            # 保存边界样本
            borderline_file = f'borderline_samples_th{threshold}_m{margin}.csv'
            borderline_df.to_csv(borderline_file, index=False, encoding='utf-8-sig')
            print(f"\n边界样本已保存至: {borderline_file}")
        else:
            print("没有找到边界样本")

    except Exception as e:
        print(f"边界样本分析失败: {e}")


# -------------------------- 7. 主执行流程 --------------------------
def main():
    # 1. 加载微博数据集
    dataset = load_merged_dataset()
    X = dataset['cleaned_review']  # 使用清洗后的评论
    y = dataset['label'].astype(int)  # 使用label列作为标签

    # 2. 文本编码
    tokenizer = Tokenizer(num_words=vocab_size, filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n', lower=True)
    tokenizer.fit_on_texts(X)
    print(f"词汇表大小：{len(tokenizer.word_index)}")  # 检查词汇表是否合理
    X_seqs = tokenizer.texts_to_sequences(X)
    X_padded = pad_sequences(X_seqs, maxlen=MAX_LEN, padding='pre', truncating='post')

    # 3. 划分训练集/验证集
    X_train_padded, X_val_padded, y_train, y_val = train_test_split(
        X_padded, y, test_size=0.2, random_state=42, stratify=y  # 测试集比例调整为20%
    )
    print(f"训练集：{len(X_train_padded)} 条，验证集：{len(X_val_padded)} 条")

    # 4. 训练模型
    model = train_model(X_train_padded, X_val_padded, y_train, y_val, tokenizer)
    del model
    gc.collect()

    # 5. 分类新评论
    classify_csv_comments()
    print("\n执行完成！")


if __name__ == '__main__':
    #main()
    # 默认使用阈值0.4（原为0.5），可调整测试其他阈值
    classify_csv_comments(threshold=0.35)
    # 测试不同阈值：
    # classify_csv_comments(threshold=0.35)  # 更宽松，减少假阴性
    # classify_csv_comments(threshold=0.45)  # 更严格
    # classify_csv_comments(threshold=0.5)   # 原始阈值