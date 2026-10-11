#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
金融文本情感分析系统主入口文件
（本地词典版，无需联网，基于CFSD中文金融情感词典）
支持CSV批量分析（针对title列）和单文本情感分析
"""

import os
import sys
import argparse
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import logging
import jieba
import warnings

# 忽略无关警告
warnings.filterwarnings('ignore', category=FutureWarning)

# ===================== 精简且兼容的字体配置（适配Matplotlib 3.9） =====================
# 核心中文字体配置（只保留一份，避免重复）
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']  # 优先级：黑体>微软雅黑>万国码
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示
plt.rcParams['pdf.fonttype'] = 42  # 关键：PDF嵌入TrueType字体，避免文字变乱码
plt.rcParams['ps.fonttype'] = 42

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 默认词典路径（替换成你的实际路径）
DEFAULT_POS_DICT = r"E:\毕业设计\newsdata\CFSD中文金融情感词典\正面词典.csv"
DEFAULT_NEG_DICT = r"E:\毕业设计\newsdata\CFSD中文金融情感词典\负面词典.csv"


class FinancialDictSentimentAnalyzer:
    """基于本地金融情感词典的分析器（无需联网）"""

    def __init__(self, pos_dict_path=DEFAULT_POS_DICT, neg_dict_path=DEFAULT_NEG_DICT):
        self.pos_words = self._load_dict(pos_dict_path)
        self.neg_words = self._load_dict(neg_dict_path) if neg_dict_path else []
        logger.info(f"加载情感词典完成：正面词{len(self.pos_words)}个，负面词{len(self.neg_words)}个")

    def _load_dict(self, dict_path):
        """加载CSV格式的情感词典"""
        try:
            # 尝试多种编码读取词典
            encodings = ['gbk', 'gb2312', 'utf-8', 'utf-8-sig']
            df = None
            for encoding in encodings:
                try:
                    df = pd.read_csv(dict_path, encoding=encoding)
                    break
                except:
                    continue

            if df is None:
                logger.error(f"无法读取词典文件: {dict_path}")
                return []

            # 取第一列作为词汇（适配CFSD词典格式）
            word_col = df.columns[0]
            words = df[word_col].dropna().astype(str).tolist()
            # 去重并过滤空字符串
            words = list(set([w.strip() for w in words if w.strip()]))
            return words
        except Exception as e:
            logger.error(f"加载词典出错: {str(e)}")
            return []

    def analyze_sentiment(self, text):
        """分析单个文本的情感（基于词典匹配）"""
        if not text or not isinstance(text, str):
            return {'score': 0.5, 'label': '中性'}

        # 分词
        words = jieba.lcut(text)
        if not words:
            return {'score': 0.5, 'label': '中性'}

        # 统计正负词数量
        pos_count = sum(1 for w in words if w in self.pos_words)
        neg_count = sum(1 for w in words if w in self.neg_words)
        total_emotion = pos_count + neg_count

        # 计算情感分数（0-1，>0.5积极，<0.5消极）
        if total_emotion == 0:
            score = 0.5
            label = '中性'
        else:
            score = pos_count / total_emotion
            if score > 0.6:
                label = '积极'
            elif score < 0.4:
                label = '消极'
            else:
                label = '中性'

        return {
            'score': score,
            'label': label,
            'pos_count': pos_count,
            'neg_count': neg_count,
            'total_emotion_words': total_emotion
        }

    def analyze_sentiment_batch(self, texts):
        """批量分析文本"""
        results = []
        for text in texts:
            results.append(self.analyze_sentiment(text))
        return results


def analyze_single_text(text, analyzer=None):
    """
    分析单个文本的情感并预测股价变动概率
    :param text: 待分析文本
    :param analyzer: 情感分析器实例
    :return: 分析结果字典
    """
    logger.info(f"开始分析文本: {text[:50]}...")

    try:
        if analyzer is None:
            analyzer = FinancialDictSentimentAnalyzer()

        result = analyzer.analyze_sentiment(text)
        logger.info("情感分析完成")

        # 获取情感分数
        sentiment_score = result['score']

        # 映射情感分数到股价涨跌概率
        if sentiment_score > 0.6:  # 积极
            up_probability = 0.5 + (sentiment_score - 0.6) * 0.75
        elif sentiment_score < 0.4:  # 消极
            up_probability = 0.5 - (0.4 - sentiment_score) * 0.75
        else:  # 中性
            up_probability = 0.45 + sentiment_score / 10

        # 确保概率在有效范围内
        up_probability = max(0.05, min(0.95, up_probability))
        down_probability = 1 - up_probability

        # 添加到结果中
        result['stock_up_probability'] = up_probability
        result['stock_down_probability'] = down_probability

        # 打印结果
        logger.info("\n金融文本分析结果:")
        logger.info(f"文本: {text[:100]}...")
        logger.info(f"情感: {result['label']} (分数: {sentiment_score:.2f})")
        logger.info(f"正面词数量: {result['pos_count']}, 负面词数量: {result['neg_count']}")

        logger.info(f"\n股价预测:")
        logger.info(f"上涨概率: {up_probability:.2f}")
        logger.info(f"下跌概率: {down_probability:.2f}")

        return result
    except Exception as e:
        import traceback
        logger.error(f"分析过程中出错: {str(e)}")
        traceback.print_exc()
        return {'error': str(e)}


def analyze_csv(input_csv, text_col="title", output_csv=None):
    """
    批量分析CSV文件中的title列
    :param input_csv: 输入CSV文件路径
    :param text_col: 文本列名（默认title）
    :param output_csv: 输出CSV文件路径
    :return: 分析结果DataFrame
    """
    logger.info(f"开始批量分析CSV文件: {input_csv}")

    try:
        # 读取CSV文件（自动适配编码）
        encodings = ['gbk', 'gb2312', 'utf-8', 'utf-8-sig']
        df = None
        for encoding in encodings:
            try:
                df = pd.read_csv(input_csv, encoding=encoding)
                logger.info(f"成功使用 {encoding} 编码读取CSV文件")
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            logger.error("错误: 无法识别CSV文件编码")
            return None

        # 检查title列是否存在
        if text_col not in df.columns:
            logger.error(f"错误: CSV文件中不存在列 '{text_col}'，当前列名列表：{df.columns.tolist()}")
            return None

        # 初始化本地词典分析器
        analyzer = FinancialDictSentimentAnalyzer()

        # 批量分析title列
        texts = df[text_col].fillna("").tolist()
        logger.info(f"开始分析 {len(texts)} 条标题文本...")

        # 批量处理
        from tqdm import tqdm
        results = []
        for text in tqdm(texts, desc="批量分析中"):
            results.append(analyzer.analyze_sentiment(text))

        # 添加分析结果到DataFrame
        df['sentiment_score'] = [r.get('score', 0.5) for r in results]
        df['sentiment_label'] = [r.get('label', '中性') for r in results]
        df['pos_word_count'] = [r.get('pos_count', 0) for r in results]
        df['neg_word_count'] = [r.get('neg_count', 0) for r in results]
        df['total_emotion_words'] = [r.get('total_emotion_words', 0) for r in results]

        # 计算股价涨跌概率
        df['up_probability'] = df['sentiment_score'].apply(
            lambda x: min(0.95, max(0.05, 0.5 + (x - 0.6) * 0.75 if x > 0.6 else
            0.5 - (0.4 - x) * 0.75 if x < 0.4 else 0.45 + x / 10))
        )
        df['down_probability'] = 1 - df['up_probability']

        # 保存结果
        if output_csv is None:
            os.makedirs("results", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_csv = os.path.join("results", f"title_sentiment_analysis_{timestamp}.csv")
        else:
            output_dir = os.path.dirname(output_csv)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        logger.info(f"分析结果已保存至: {output_csv}")

        # 生成可视化报告
        generate_analysis_report(df, output_csv.replace('.csv', '_report.pdf'))

        return df
    except Exception as e:
        import traceback
        logger.error(f"批量分析过程中出错: {str(e)}")
        traceback.print_exc()
        return None


def generate_analysis_report(df, output_file):
    """生成分析报告（修复Matplotlib 3.9参数兼容问题）"""
    try:
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        sns.set(style="whitegrid", font='SimHei')  # 绘图库全局指定黑体
        plt.figure(figsize=(15, 12), dpi=100)  # 提升基础分辨率

        # 定义字体配置（移除pad参数，pad作为title独立参数传入）
        font_config = {'family': 'SimHei', 'size': 12, 'weight': 'normal'}
        title_font = {'family': 'SimHei', 'size': 14, 'weight': 'bold'}  # 移除pad

        # 1. 情感分布饼图
        plt.subplot(2, 2, 1)
        sentiment_counts = df['sentiment_label'].value_counts()
        color_map = {'积极': '#99ff99', '中性': '#66b3ff', '消极': '#ff9999'}
        colors = [color_map[label] for label in sentiment_counts.index]
        plt.pie(sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%', colors=colors, startangle=90)
        # pad作为独立参数传入plt.title()，而非fontdict
        plt.title('标题情感分布', fontdict=title_font, pad=20)

        # 2. 情感分数直方图
        plt.subplot(2, 2, 2)
        sns.histplot(df['sentiment_score'], bins=20, kde=True, color='#66b3ff')
        plt.title('标题情感分数分布', fontdict=title_font, pad=20)
        plt.xlabel('情感分数', fontdict=font_config)
        plt.ylabel('频率', fontdict=font_config)

        # 3. 上涨概率直方图
        plt.subplot(2, 2, 3)
        sns.histplot(df['up_probability'], bins=20, kde=True, color='#99ff99')
        plt.title('标题对应上涨概率分布', fontdict=title_font, pad=20)
        plt.xlabel('上涨概率', fontdict=font_config)
        plt.ylabel('频率', fontdict=font_config)

        # 4. 情感标签与上涨概率关系
        plt.subplot(2, 2, 4)
        sns.boxplot(
            x='sentiment_label',
            y='up_probability',
            data=df,
            hue='sentiment_label',
            palette=color_map,
            legend=False
        )
        plt.title('标题情感与上涨概率关系', fontdict=title_font, pad=20)
        plt.xlabel('情感标签', fontdict=font_config)
        plt.ylabel('上涨概率', fontdict=font_config)

        # 优化PDF保存参数
        plt.tight_layout(pad=3.0)
        plt.savefig(
            output_file,
            dpi=300,
            bbox_inches='tight',
            format='pdf',
            transparent=False,
            facecolor='white'
        )
        plt.close()

        logger.info(f"分析报告已保存至: {output_file}")

    except Exception as e:
        logger.error(f"生成报告出错: {str(e)}")
        import traceback
        traceback.print_exc()


def combine_risk_with_sentiment(risk_result_text, sentiment_result_texts, stock_name=None, stock_code=None):
    """
    将舆情分析模块的舆情分析结果融入风险分析模块，生成综合风险评估。

    当LLM同时调用了风险分析工具（行动1）和舆情分析工具（行动2）时，
    此函数提取舆情分析中的评论情感数据，结合风险分析中的新闻情感数据，
    给出更全面的综合风险评估，并替换原始的风险分析结果。

    Parameters
    ----------
    risk_result_text : str
        风险分析模块生成的原始结果文本（含新闻情感评分和风险等级）
    sentiment_result_texts : list of str
        舆情分析模块生成的结果文本列表（含评论情感分析）
    stock_name : str, optional
        股票名称，若不提供则尝试从文本中提取
    stock_code : str, optional
        股票代码，若不提供则尝试从文本中提取

    Returns
    -------
    str
        更新后的综合风险评估文本。如果舆情数据不可用或解析失败，
        则原样返回 risk_result_text。
    """
    import re

    # ========== 1. 从风险分析文本中提取股票名称和代码 ==========
    if not stock_name:
        for line in risk_result_text.split('\n'):
            m = re.search(r'股票名称：(.+?)（', line)
            if m:
                stock_name = m.group(1).strip()
                break
    if not stock_code:
        for line in risk_result_text.split('\n'):
            m = re.search(r'代码：(.+?)）', line)
            if m:
                stock_code = m.group(1).strip()
                break
            m = re.search(r'代码：(\S+)', line)
            if m:
                stock_code = m.group(1).strip()
                break

    stock_label = stock_name or "未知"
    code_label = stock_code or ""

    # ========== 2. 解析风险分析结果（新闻情感数据） ==========
    avg_score = None
    news_pos = news_neg = news_neu = 0
    total_news = 0

    for line in risk_result_text.split('\n'):
        m = re.search(r'平均情感分数：(\d+\.\d+)', line)
        if m:
            avg_score = float(m.group(1))
        m = re.search(r'积极新闻：(\d+)条', line)
        if m:
            news_pos = int(m.group(1))
        m = re.search(r'消极新闻：(\d+)条', line)
        if m:
            news_neg = int(m.group(1))
        m = re.search(r'中性新闻：(\d+)条', line)
        if m:
            news_neu = int(m.group(1))
        m = re.search(r'新闻数量：(\d+)', line)
        if m:
            total_news = int(m.group(1))

    # ========== 3. 解析舆情分析结果（评论情感数据） ==========
    total_comments = 0
    sent_pos = sent_neg = 0
    sent_pos_ratio = 0.0
    sent_neg_ratio = 0.0
    sentiment_summary = ""

    for sent_text in sentiment_result_texts:
        # 只处理与当前股票相关的舆情结果
        if stock_name and stock_name not in sent_text:
            continue
        for line in sent_text.split('\n'):
            m = re.search(r'总评论数：(\d+)条', line)
            if m:
                total_comments = int(m.group(1))
            m = re.search(r'积极评论：(\d+)条.*?([\d.]+%)', line)
            if m:
                sent_pos = int(m.group(1))
                sent_pos_ratio = float(m.group(2).replace('%', '')) / 100
            m = re.search(r'消极评论：(\d+)条.*?([\d.]+%)', line)
            if m:
                sent_neg = int(m.group(1))
                sent_neg_ratio = float(m.group(2).replace('%', '')) / 100
            m = re.search(r'舆情总结：(.+)', line)
            if m:
                sentiment_summary = m.group(1).strip()
        break  # 只匹配第一个相关的舆情结果

    # 若没有匹配到舆情数据，直接返回原始风险分析结果
    if total_comments == 0:
        return risk_result_text

    # ========== 4. 计算综合情感分数 ==========
    # 舆情分数：积极比例越高分数越高
    forum_score = sent_pos_ratio

    if avg_score is not None:
        # 自适应权重：新闻数少时舆情权重高，反之亦然
        news_weight = min(total_news, 30) / (min(total_news, 30) + min(total_comments / 5, 30))
        forum_weight = 1 - news_weight
        combined_score = avg_score * news_weight + forum_score * forum_weight
    else:
        combined_score = forum_score

    # ========== 5. 确定综合风险等级 ==========
    if combined_score > 0.6:
        combined_risk = "较低风险（积极情绪主导）"
        combined_level = "低"
    elif combined_score < 0.4:
        combined_risk = "较高风险（消极情绪主导）"
        combined_level = "高"
    else:
        combined_risk = "中等风险（情绪中性）"
        combined_level = "中"

    # ========== 6. 判断新闻与舆情是否一致 ==========
    if avg_score is not None:
        if avg_score > 0.6:
            news_direction = "积极"
        elif avg_score < 0.4:
            news_direction = "消极"
        else:
            news_direction = "中性"

    if sent_pos_ratio > 0.6:
        forum_direction = "积极"
    elif sent_neg_ratio > 0.6:
        forum_direction = "消极"
    else:
        forum_direction = "中性"

    # 方向一致性判断
    direction_match = (news_direction == forum_direction) if avg_score is not None else False

    # ========== 7. 构建综合评估说明 ==========
    explanation_parts = []
    explanation_parts.append(
        f"新闻情感评分：{avg_score:.3f}（{news_direction}）" if avg_score is not None else "新闻情感评分：无数据"
    )
    explanation_parts.append(f"舆情积极比例：{sent_pos_ratio:.1%}，消极比例：{sent_neg_ratio:.1%}（{forum_direction}）")

    if direction_match and news_direction != "中性":
        explanation_parts.append(
            f"新闻情感与舆情情绪均偏{news_direction}，方向一致，评估置信度较高"
        )
    elif news_direction != "中性" and forum_direction != "中性":
        explanation_parts.append(
            f"新闻情感偏{news_direction}但舆情情绪偏{forum_direction}，存在分歧，综合评级趋于保守"
        )
    else:
        explanation_parts.append("综合新闻与舆情数据得出以下评级")

    explanation = "；".join(explanation_parts)

    # ========== 8. 生成综合风险评估文本 ==========
    code_part = f" ({code_label})" if code_label else ""
    combined_text = f"【综合风险评估 - {stock_label}{code_part}】\n"
    combined_text += f"股票名称：{stock_label}"
    combined_text += f"（代码：{code_label}）\n" if code_label else "\n"
    combined_text += f"  ── 新闻情感分析（风险分析模块）──\n"
    combined_text += f"  新闻数量：{total_news}条\n"
    combined_text += f"  积极新闻：{news_pos}条，消极新闻：{news_neg}条，中性新闻：{news_neu}条\n"
    if avg_score is not None:
        combined_text += f"  平均情感分数：{avg_score:.3f}\n"
    combined_text += f"  ── 舆情情感分析（舆情分析模块）──\n"
    combined_text += f"  总评论数：{total_comments}条\n"
    combined_text += f"  积极评论：{sent_pos}条（{sent_pos_ratio:.1%}）\n"
    combined_text += f"  消极评论：{sent_neg}条（{sent_neg_ratio:.1%}）\n"
    combined_text += f"  舆情总结：{sentiment_summary}\n"
    combined_text += f"  ── 综合风险评估 ──\n"
    combined_text += f"  综合情感分数：{combined_score:.3f}\n"
    combined_text += f"  综合风险评级：{combined_risk}\n"
    combined_text += f"  评估说明：{explanation}\n"
    combined_text += "-" * 50 + "\n"

    return combined_text


def main():
    # 固定分析文件路径
    INPUT_CSV_PATH = r"stock_news.csv"
    TEXT_COL = "title"

    # 检查文件是否存在
    if not os.path.exists(INPUT_CSV_PATH):
        logger.error(f"错误：指定的CSV文件不存在！路径：{INPUT_CSV_PATH}")
        return

    # 直接调用批量分析函数
    analyze_csv(INPUT_CSV_PATH, TEXT_COL)


if __name__ == "__main__":
    # 安装必要依赖（首次运行自动安装）
    try:
        import jieba
        import tqdm
    except ImportError:
        logger.info("正在安装必要依赖...")
        os.system(f"{sys.executable} -m pip install jieba tqdm seaborn matplotlib pandas")
        import jieba
        import tqdm

    main()