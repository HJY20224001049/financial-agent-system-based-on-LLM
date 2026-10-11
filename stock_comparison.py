# -*- coding: UTF-8 -*-
"""
股票预测模型对比实验
包括：LSTM（原模型）、SVM、Transformer、随机森林、XGBoost
使用相同的数据集和评估指标进行公平比较
"""

import pandas as pd
import numpy as np
import os
import sys
import time
import logging
from logging.handlers import RotatingFileHandler
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

# 设置随机种子
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

class Config:
    # 数据参数
    feature_columns = list(range(2, 9))     # 要作为feature的列，按原数据从0开始计算
    label_columns = [4, 5]                  # 要预测的列，按原数据从0开始计算, 如同时预测第四，五列 最低价和最高价
    label_in_feature_index = (lambda x,y: [x.index(i) for i in y])(feature_columns, label_columns)  # 因为feature不一定从0开始

    predict_day = 1             # 预测未来几天

    # 网络参数（主要用于LSTM和Transformer）
    input_size = len(feature_columns)
    output_size = len(label_columns)

    hidden_size = 128           # LSTM的隐藏层大小，也是输出大小
    lstm_layers = 2             # LSTM的堆叠层数
    dropout_rate = 0.3          # dropout概率
    time_step = 20              # 用前多少天的数据来预测

    # 训练参数
    do_train = True
    do_predict = True
    add_train = False          # 是否载入已有模型参数进行增量训练
    shuffle_train_data = True   # 是否对训练数据做shuffle
    use_cuda = False            # 是否使用GPU训练

    train_data_rate = 0.95      # 训练数据占总体数据比例，测试数据就是 1-train_data_rate
    valid_data_rate = 0.15      # 验证数据占训练数据比例，验证集在训练过程使用，为了做模型和参数选择

    batch_size = 64
    learning_rate = 0.0005
    epoch = 20                  # 整个训练集被训练多少遍，不考虑早停的前提下
    patience = 5                # 训练多少epoch，验证集没提升就停掉
    random_seed = SEED          # 随机种子，保证可复现

    # 路径参数
    train_data_path = "./data/stock_data.csv"
    model_save_path = "./comparison_models/"
    figure_save_path = "./comparison_results/figures/"
    log_save_path = "./comparison_results/logs/"
    result_save_path = "./comparison_results/"

    do_log_print_to_screen = True
    do_log_save_to_file = True
    do_figure_save = True

    # 创建目录
    for path in [model_save_path, figure_save_path, log_save_path, result_save_path]:
        if not os.path.exists(path):
            os.makedirs(path)

    # Transformer参数
    transformer_d_model = 64  # 模型维度
    transformer_nhead = 4     # 注意力头数
    transformer_num_layers = 2  # 编码器层数
    transformer_dim_feedforward = 256  # 前馈网络维度
    transformer_dropout = 0.1

    # SVM和树模型参数
    svm_kernel = 'rbf'
    svm_C = 1.0
    svm_gamma = 'scale'

    rf_n_estimators = 10
    rf_max_depth = None

    xgb_n_estimators = 10
    xgb_max_depth = 6
    xgb_learning_rate = 0.1

    dt_max_depth = 5


class StockDataProcessor:
    """股票数据处理器，为不同模型准备数据"""

    def __init__(self, config):
        self.config = config
        self.data, self.data_column_name = self.read_data()

        self.data_num = self.data.shape[0]
        self.train_num = int(self.data_num * self.config.train_data_rate)

        # 归一化
        self.mean = np.mean(self.data, axis=0)
        self.std = np.std(self.data, axis=0)
        self.norm_data = (self.data - self.mean) / self.std

        self.start_num_in_test = 0

    def read_data(self):
        """读取初始数据"""
        init_data = pd.read_csv(self.config.train_data_path,
                               usecols=self.config.feature_columns)
        return init_data.values, init_data.columns.tolist()

    def prepare_sequences(self):
        """准备时间序列数据（用于LSTM、Transformer等序列模型）"""
        feature_data = self.norm_data[:self.train_num]
        label_data = self.norm_data[self.config.predict_day:self.config.predict_day + self.train_num,
                                   self.config.label_in_feature_index]

        # 创建序列样本
        train_x = [feature_data[i:i+self.config.time_step]
                  for i in range(self.train_num - self.config.time_step)]
        train_y = [label_data[i:i+self.config.time_step]
                  for i in range(self.train_num - self.config.time_step)]

        train_x, train_y = np.array(train_x), np.array(train_y)

        # 划分训练集和验证集
        train_x, valid_x, train_y, valid_y = train_test_split(
            train_x, train_y,
            test_size=self.config.valid_data_rate,
            random_state=self.config.random_seed,
            shuffle=self.config.shuffle_train_data
        )

        # 准备测试集
        feature_data_test = self.norm_data[self.train_num:]
        sample_interval = min(feature_data_test.shape[0], self.config.time_step)
        self.start_num_in_test = feature_data_test.shape[0] % sample_interval
        time_step_size = feature_data_test.shape[0] // sample_interval

        test_x = [feature_data_test[self.start_num_in_test + i*sample_interval:
                                   self.start_num_in_test + (i+1)*sample_interval]
                 for i in range(time_step_size)]

        # 构建测试集标签，与训练集逻辑一致：标签偏移predict_day天
        # 标签起始位置需要加上predict_day偏移
        label_start = self.train_num + self.start_num_in_test + self.config.predict_day
        # 确保不超过数据范围
        max_available = self.data_num - label_start
        if max_available < time_step_size * sample_interval:
            # 如果未来数据不足，调整time_step_size
            time_step_size = max_available // sample_interval
            if time_step_size <= 0:
                raise ValueError("测试集未来数据不足，无法构建标签")
            # 同时需要调整test_x
            test_x = test_x[:time_step_size]

        label_data_test = self.norm_data[label_start:label_start + time_step_size * sample_interval,
                                        self.config.label_in_feature_index]
        # 将标签数据重塑为序列，形状与test_x对应
        # label_data_test形状: [time_step_size * sample_interval, output_size]
        # 重塑为: [time_step_size, sample_interval, output_size]
        test_y = label_data_test.reshape(time_step_size, sample_interval, -1)

        return (train_x, train_y, valid_x, valid_y,
                np.array(test_x), test_y)

    def prepare_flattened_data(self):
        """准备扁平化数据（用于SVM、随机森林等传统模型）"""
        train_x, train_y, valid_x, valid_y, test_x, test_y = self.prepare_sequences()

        # 将序列数据展平 [样本数, time_step, 特征数] -> [样本数, time_step*特征数]
        train_x_flat = train_x.reshape(train_x.shape[0], -1)
        valid_x_flat = valid_x.reshape(valid_x.shape[0], -1)
        test_x_flat = test_x.reshape(test_x.shape[0], -1)

        # 标签取最后一个时间步的预测（因为我们用time_step天的数据预测下一天）
        # train_y形状: [样本数, time_step, 输出维度]
        # 我们只关心第predict_day天的预测，但原标签已经是偏移后的
        # 简化：取每个样本的最后一个时间步的标签作为目标
        train_y_flat = train_y[:, -1, :]  # 取每个序列的最后一个时间步
        valid_y_flat = valid_y[:, -1, :]
        # test_y现在也是三维的[样本数, sample_interval, 输出维度]，取最后一个时间步
        if len(test_y.shape) == 3:
            test_y_flat = test_y[:, -1, :]
        else:
            test_y_flat = test_y  # 保持向后兼容

        return (train_x_flat, train_y_flat, valid_x_flat, valid_y_flat,
                test_x_flat, test_y_flat)

    def prepare_single_step_data(self):
        """准备单步预测数据（每个样本只预测一个时间点）"""
        train_x, train_y, valid_x, valid_y, test_x, test_y = self.prepare_sequences()

        # 将序列数据展平，并且每个时间步作为一个独立样本
        # 这对某些模型可能更合适
        train_samples = train_x.shape[0] * train_x.shape[1]  # 样本数 * time_step
        valid_samples = valid_x.shape[0] * valid_x.shape[1]
        test_samples = test_x.shape[0] * test_x.shape[1]

        train_x_single = train_x.reshape(-1, train_x.shape[2])
        train_y_single = train_y.reshape(-1, train_y.shape[2])

        valid_x_single = valid_x.reshape(-1, valid_x.shape[2])
        valid_y_single = valid_y.reshape(-1, valid_y.shape[2])

        test_x_single = test_x.reshape(-1, test_x.shape[2])
        # test_y现在是三维的[样本数, sample_interval, 输出维度]，重塑为二维
        if len(test_y.shape) == 3:
            test_y_single = test_y.reshape(-1, test_y.shape[2])
        else:
            test_y_single = np.repeat(test_y, test_x.shape[1], axis=0)  # 保持向后兼容

        return (train_x_single, train_y_single, valid_x_single, valid_y_single,
                test_x_single, test_y_single)

    def inverse_normalize(self, norm_data, is_label=True):
        """将归一化数据反归一化"""
        if is_label:
            indices = self.config.label_in_feature_index
            std = self.std[indices]
            mean = self.mean[indices]
        else:
            std = self.std
            mean = self.mean

        return norm_data * std + mean

    def get_feature_dim(self):
        """获取特征维度"""
        return self.config.input_size

    def get_output_dim(self):
        """获取输出维度"""
        return self.config.output_size


def load_logger(config):
    """配置日志"""
    logger = logging.getLogger()
    logger.setLevel(level=logging.DEBUG)

    # StreamHandler
    if config.do_log_print_to_screen:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(level=logging.INFO)
        formatter = logging.Formatter(datefmt='%Y/%m/%d %H:%M:%S',
                                      fmt='[ %(asctime)s ] %(message)s')
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    # FileHandler
    if config.do_log_save_to_file:
        log_file = config.log_save_path + f"comparison_experiment_{time.strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = RotatingFileHandler(log_file, maxBytes=1024000, backupCount=5)
        file_handler.setLevel(level=logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 记录配置信息
        config_dict = {}
        for key in dir(config):
            if not key.startswith("_"):
                config_dict[key] = getattr(config, key)
        config_str = str(config_dict)
        config_list = config_str[1:-1].split(", '")
        config_save_str = "\nConfig:\n" + "\n'".join(config_list)
        logger.info(config_save_str)

    return logger


if __name__ == "__main__":
    # 测试数据处理器
    config = Config()
    processor = StockDataProcessor(config)

    # 测试序列数据
    train_x_seq, train_y_seq, valid_x_seq, valid_y_seq, test_x_seq, test_y_seq = processor.prepare_sequences()
    print(f"序列数据形状:")
    print(f"  train_x_seq: {train_x_seq.shape}")
    print(f"  train_y_seq: {train_y_seq.shape}")
    print(f"  test_x_seq: {test_x_seq.shape}")
    print(f"  test_y_seq: {test_y_seq.shape}")

    # 测试扁平化数据
    train_x_flat, train_y_flat, valid_x_flat, valid_y_flat, test_x_flat, test_y_flat = processor.prepare_flattened_data()
    print(f"\n扁平化数据形状:")
    print(f"  train_x_flat: {train_x_flat.shape}")
    print(f"  train_y_flat: {train_y_flat.shape}")
    print(f"  test_x_flat: {test_x_flat.shape}")
    print(f"  test_y_flat: {test_y_flat.shape}")