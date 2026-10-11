# -*- coding: UTF-8 -*-
"""
@author: hichenway
@知乎: 海晨威
@contact: lyshello123@163.com
@time: 2020/5/9 17:00
@license: Apache
主程序：包括配置，数据读取，日志记录，绘图，模型训练和预测
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

frame = "pytorch"
if frame == "pytorch":
    from stock_model.model_pytorch import train, predict
else:
    raise Exception("Wrong frame seletion")

class Config:
    # 数据参数
    feature_columns = list(range(2, 9))     # 要作为feature的列，按原数据从0开始计算，也可以用list 如 [2,4,6,8] 设置
    label_columns = [4, 5]                  # 要预测的列，按原数据从0开始计算, 如同时预测第四，五列 最低价和最高价
    # label_in_feature_index = [feature_columns.index(i) for i in label_columns]  # 这样写不行
    label_in_feature_index = (lambda x,y: [x.index(i) for i in y])(feature_columns, label_columns)  # 因为feature不一定从0开始

    predict_day = 1             # 预测未来几天

    # 网络参数
    input_size = len(feature_columns)
    output_size = len(label_columns)

    hidden_size = 128           # LSTM的隐藏层大小，也是输出大小
    lstm_layers = 2             # LSTM的堆叠层数
    dropout_rate = 0.2          # dropout概率
    time_step = 20              # 这个参数很重要，是设置用前多少天的数据来预测，也是LSTM的time step数，保证训练数据量大于它

    # 训练参数
    do_train = False
    do_predict = True
    add_train = True          # 是否载入已有模型参数进行增量训练
    shuffle_train_data = True   # 是否对训练数据做shuffle
    use_cuda = False            # 是否使用GPU训练

    train_data_rate = 0.95      # 训练数据占总体数据比例，测试数据就是 1-train_data_rate
    valid_data_rate = 0.15      # 验证数据占训练数据比例，验证集在训练过程使用，为了做模型和参数选择

    batch_size = 64
    learning_rate = 0.001
    epoch = 20                  # 整个训练集被训练多少遍，不考虑早停的前提下
    patience = 5                # 训练多少epoch，验证集没提升就停掉
    random_seed = 42            # 随机种子，保证可复现

    do_continue_train = False    # 每次训练把上一次的final_state作为下一次的init_state，仅用于RNN类型模型，目前仅支持pytorch
    continue_flag = ""           # 但实际效果不佳，可能原因：仅能以 batch_size = 1 训练
    if do_continue_train:
        
        shuffle_train_data = False
        batch_size = 1
        continue_flag = "continue_"

    # 训练模式
    debug_mode = False  # 调试模式下，是为了跑通代码，追求快
    debug_num = 500  # 仅用debug_num条数据来调试

    # 框架参数
    used_frame = frame  # 选择的深度学习框架，不同的框架模型保存后缀不一样
    model_postfix = {"pytorch": ".pth", "keras": ".h5", "tensorflow": ".ckpt"}
    model_name = "model_" + continue_flag + used_frame + model_postfix[used_frame]

    # 路径参数
    train_data_path = "./data/stock_data.csv"
    model_save_path = "./checkpoint/" + used_frame + "/"
    figure_save_path = "./figure/"
    log_save_path = "./log/"
    do_log_print_to_screen = True
    do_log_save_to_file = True                  # 是否将config和训练过程记录到log
    do_figure_save = False
    do_train_visualized = False          # 训练loss可视化，pytorch用visdom，tf用tensorboardX，实际上可以通用, keras没有
    recent_days_to_show = 30             # 折线图显示最近多少天的数据

    # 置信区间参数
    confidence_level = 0.95               # 置信水平: 0.90, 0.95, 0.99
    use_standard_error = True            # 是否使用标准误差(True: std_error/sqrt(n), False: std_error)
    confidence_interval_scale = 1.0      # 置信区间宽度缩放因子，小于1缩小，大于1放大
    smooth_errors = False                # 是否对误差进行平滑处理（移动平均）
    smooth_window = 10                   # 平滑窗口大小
    dynamic_confidence = True            # 是否使用动态置信区间计算(True: 滑动窗口, False: 全局标准差)
    if not os.path.exists(model_save_path):
        os.makedirs(model_save_path)    # makedirs 递归创建目录
    if not os.path.exists(figure_save_path):
        os.mkdir(figure_save_path)
    if do_train and (do_log_save_to_file or do_train_visualized):
        cur_time = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime())
        log_save_path = log_save_path + cur_time + '_' + used_frame + "/"
        os.makedirs(log_save_path)


class Data:
    def __init__(self, config):
        self.config = config
        self.data, self.data_column_name = self.read_data()

        self.data_num = self.data.shape[0]
        self.train_num = int(self.data_num * self.config.train_data_rate)

        self.mean = np.mean(self.data, axis=0)              # 数据的均值和方差
        self.std = np.std(self.data, axis=0)
        self.norm_data = (self.data - self.mean)/self.std   # 归一化，去量纲

        self.start_num_in_test = 0      # 测试集中前几天的数据会被删掉，因为它不够一个time_step

    def read_data(self):                # 读取初始数据
        if self.config.debug_mode:
            init_data = pd.read_csv(self.config.train_data_path, nrows=self.config.debug_num,
                                    usecols=self.config.feature_columns)
        else:
            init_data = pd.read_csv(self.config.train_data_path, usecols=self.config.feature_columns)
        return init_data.values, init_data.columns.tolist()     # .columns.tolist() 是获取列名

    def get_train_and_valid_data(self):
        feature_data = self.norm_data[:self.train_num]
        label_data = self.norm_data[self.config.predict_day : self.config.predict_day + self.train_num,
                                    self.config.label_in_feature_index]    # 将延后几天的数据作为label

        if not self.config.do_continue_train:
            # 在非连续训练模式下，每time_step行数据会作为一个样本，两个样本错开一行，比如：1-20行，2-21行。。。。
            train_x = [feature_data[i:i+self.config.time_step] for i in range(self.train_num-self.config.time_step)]
            train_y = [label_data[i:i+self.config.time_step] for i in range(self.train_num-self.config.time_step)]
        else:
            # 在连续训练模式下，每time_step行数据会作为一个样本，两个样本错开time_step行，
            # 比如：1-20行，21-40行。。。到数据末尾，然后又是 2-21行，22-41行。。。到数据末尾，……
            # 这样才可以把上一个样本的final_state作为下一个样本的init_state，而且不能shuffle
            # 目前本项目中仅能在pytorch的RNN系列模型中用
            train_x = [feature_data[start_index + i*self.config.time_step : start_index + (i+1)*self.config.time_step]
                       for start_index in range(self.config.time_step)
                       for i in range((self.train_num - start_index) // self.config.time_step)]
            train_y = [label_data[start_index + i*self.config.time_step : start_index + (i+1)*self.config.time_step]
                       for start_index in range(self.config.time_step)
                       for i in range((self.train_num - start_index) // self.config.time_step)]

        train_x, train_y = np.array(train_x), np.array(train_y)

        train_x, valid_x, train_y, valid_y = train_test_split(train_x, train_y, test_size=self.config.valid_data_rate,
                                                              random_state=self.config.random_seed,
                                                              shuffle=self.config.shuffle_train_data)   # 划分训练和验证集，并打乱
        return train_x, valid_x, train_y, valid_y

    def get_test_data(self, return_label_data=False):
        feature_data = self.norm_data[self.train_num:]
        sample_interval = min(feature_data.shape[0], self.config.time_step)     # 防止time_step大于测试集数量
        self.start_num_in_test = feature_data.shape[0] % sample_interval  # 这些天的数据不够一个sample_interval
        time_step_size = feature_data.shape[0] // sample_interval

        # 在测试数据中，每time_step行数据会作为一个样本，两个样本错开time_step行
        # 比如：1-20行，21-40行。。。到数据末尾。
        test_x = [feature_data[self.start_num_in_test+i*sample_interval : self.start_num_in_test+(i+1)*sample_interval]
                   for i in range(time_step_size)]
        if return_label_data:       # 实际应用中的测试集是没有label数据的
            label_data = self.norm_data[self.train_num + self.start_num_in_test:, self.config.label_in_feature_index]
            return np.array(test_x), label_data
        return np.array(test_x)

def load_logger(config):
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
        file_handler = RotatingFileHandler(config.log_save_path + "out.log", maxBytes=1024000, backupCount=5)
        file_handler.setLevel(level=logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 把config信息也记录到log 文件中
        config_dict = {}
        for key in dir(config):
            if not key.startswith("_"):
                config_dict[key] = getattr(config, key)
        config_str = str(config_dict)
        config_list = config_str[1:-1].split(", '")
        config_save_str = "\nConfig:\n" + "\n'".join(config_list)
        logger.info(config_save_str)

    return logger

def draw(config: Config, origin_data: Data, logger, predict_norm_data: np.ndarray):
    # 设置中文字体支持，确保图表中的中文正常显示
    try:
        import matplotlib
        import platform
        system = platform.system()

        if system == 'Windows':
            # Windows系统字体路径
            font_paths = [
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
                'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
                'C:/Windows/Fonts/msyhbd.ttc',  # 微软雅黑粗体
                'C:/Windows/Fonts/simkai.ttf',  # 楷体
            ]
        elif system == 'Linux':
            # Linux系统字体路径
            font_paths = [
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            ]
        else:  # macOS
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/STHeiti Medium.ttc',
            ]

        # 尝试添加可用的中文字体
        font_added = False
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    matplotlib.font_manager.fontManager.addfont(font_path)
                    font_name = matplotlib.font_manager.FontProperties(fname=font_path).get_name()
                    plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams['font.sans-serif']
                    font_added = True
                    print(f"已添加中文字体: {font_name} (路径: {font_path})")
                    break
                except Exception as e:
                    print(f"添加字体失败 {font_path}: {e}")

        # 如果未添加成功，使用默认字体列表
        if not font_added:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']

        plt.rcParams['axes.unicode_minus'] = False
        print("中文字体设置完成")
    except Exception as e:
        print(f"中文字体设置失败，将使用默认字体: {e}")
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            pass

    label_data = origin_data.data[origin_data.train_num + origin_data.start_num_in_test : ,
                                            config.label_in_feature_index]
    predict_data = predict_norm_data * origin_data.std[config.label_in_feature_index] + \
                   origin_data.mean[config.label_in_feature_index]   # 通过保存的均值和方差还原数据
    assert label_data.shape[0]==predict_data.shape[0], "The element number in origin and predicted data is different"

    label_name = [origin_data.data_column_name[i] for i in config.label_in_feature_index]
    label_column_num = len(config.label_columns)

    # label 和 predict 是错开config.predict_day天的数据的
    # 下面是两种norm后的loss的计算方式，结果是一样的，可以简单手推一下
    # label_norm_data = origin_data.norm_data[origin_data.train_num + origin_data.start_num_in_test:,
    #              config.label_in_feature_index]
    # loss_norm = np.mean((label_norm_data[config.predict_day:] - predict_norm_data[:-config.predict_day]) ** 2, axis=0)
    # logger.info("The mean squared error of stock {} is ".format(label_name) + str(loss_norm))

    loss = np.mean((label_data[config.predict_day:] - predict_data[:-config.predict_day] ) ** 2, axis=0)
    loss_norm = loss/(origin_data.std[config.label_in_feature_index] ** 2)
    logger.info("The mean squared error of stock {} is ".format(label_name) + str(loss_norm))
    # 计算预测误差的标准差，用于置信区间
    error = label_data[config.predict_day:] - predict_data[:-config.predict_day]
    if error.shape[0] > 0:
        std_error = np.std(error, axis=0)  # 每个标签列的标准差
        logger.info("Standard deviation of prediction error for {} is ".format(label_name) + str(std_error))

        # 根据配置调整误差估计
        if config.use_standard_error:
            n_samples = error.shape[0]
            adjusted_error = std_error / np.sqrt(n_samples)
            logger.info("Using standard error (divided by sqrt({}))".format(n_samples))
        else:
            adjusted_error = std_error
            logger.info("Using raw standard deviation")

        # 获取置信水平对应的z值
        z_values = {
            0.80: 1.282,
            0.85: 1.440,
            0.90: 1.645,
            0.95: 1.960,
            0.99: 2.576
        }
        confidence_z = z_values.get(config.confidence_level, 1.96)  # 默认95%
        logger.info("Confidence level: {}%, z-value: {:.3f}".format(
            config.confidence_level * 100, confidence_z))
    else:
        std_error = np.zeros(len(label_name))
        adjusted_error = np.zeros(len(label_name))
        confidence_z = 1.96
        logger.info("No error data available for confidence interval, setting std_error to zero")

    label_X = range(origin_data.data_num - origin_data.train_num - origin_data.start_num_in_test)
    predict_X = [ x + config.predict_day for x in label_X]

    # 只显示最近recent_days_to_show天的数据
    recent_days = config.recent_days_to_show
    total_days = len(label_X)
    if total_days > recent_days:
        start_idx = total_days - recent_days
        label_X = list(label_X)[start_idx:]  # 转换为列表再切片
        predict_X = predict_X[start_idx:]
        label_data = label_data[start_idx:]
        predict_data = predict_data[start_idx:]
    else:
        # 如果总天数不超过recent_days天，显示所有数据
        label_X = list(label_X)

    if not sys.platform.startswith('linux'):    # 无桌面的Linux下无法输出，如果是有桌面的Linux，如Ubuntu，可去掉这一行
        # 计算预测误差（用于置信区间）
        # 注意：label_data和predict_data已经根据recent_days_to_show切片，但误差计算需要对齐
        # 由于label_data和predict_data错开config.predict_day天，误差计算为：
        # error = label_data[config.predict_day:] - predict_data[:-config.predict_day]
        # 但需要考虑切片后的索引
        # 简单方法：重新计算切片后的误差
        if len(label_data) > config.predict_day:
            # 对齐数据计算误差
            error = label_data[config.predict_day:] - predict_data[:-config.predict_day]
        else:
            error = np.zeros((0, label_column_num))

        # 误差平滑处理（如果需要）
        if config.smooth_errors and error.shape[0] > 0:
            # 确保平滑窗口不超过误差序列长度
            effective_window = min(config.smooth_window, error.shape[0])
            if effective_window < 2:
                logger.info("Error sequence too short for smoothing, skipping")
            else:
                logger.info(f"Applying error smoothing with window size {effective_window}")
                smoothed_error = np.zeros_like(error)
                for i in range(label_column_num):
                    error_i = error[:, i]
                    # 使用numpy进行移动平均平滑
                    kernel = np.ones(effective_window) / effective_window
                    smoothed = np.convolve(error_i, kernel, mode='same')
                    # 处理边界效应：使用前向/后向填充
                    half_window = effective_window // 2
                    if half_window > 0:
                        # 确保索引不越界
                        if half_window < len(smoothed):
                            smoothed[:half_window] = smoothed[half_window]
                        # 右边界
                        if len(smoothed) - half_window - 1 >= 0:
                            smoothed[-half_window:] = smoothed[-half_window-1]
                    smoothed_error[:, i] = smoothed
                error = smoothed_error
                logger.info("Error smoothing applied")

        # 为每个标签维度计算置信区间
        confidence_intervals = []  # 存储每个维度的(confidence_lower, confidence_upper)

        logger.info(f"Confidence interval parameters:")
        logger.info(f"  Confidence level: {config.confidence_level*100:.1f}%, z-value: {confidence_z:.3f}")
        logger.info(f"  Use standard error: {config.use_standard_error}")
        logger.info(f"  Confidence interval scale: {config.confidence_interval_scale}")
        logger.info(f"  Smooth errors: {config.smooth_errors}, window: {config.smooth_window}")
        logger.info(f"  Dynamic confidence: {config.dynamic_confidence}")

        if config.dynamic_confidence:
            # 动态置信区间计算（滑动窗口）
            logger.info("Using dynamic confidence intervals (sliding window)")
            for i in range(label_column_num):
                n_samples = len(predict_data[:, i])
                # 动态计算窗口大小：样本数的10%，但范围在10到50之间
                window_size = max(10, min(50, int(n_samples * 0.1)))
                confidence_upper = np.zeros(n_samples)
                confidence_lower = np.zeros(n_samples)

                # 获取当前维度的误差序列
                if error.shape[0] > 0:
                    error_i = error[:, i]
                    # 计算全局误差标准差作为后备
                    global_error_std = np.std(error_i, ddof=0) if len(error_i) > 0 else 0.0

                    for t in range(n_samples):
                        # 计算窗口内的误差标准差
                        # 注意：预测值的时间点t对应的误差可能需要偏移
                        # 简单假设：使用最近的误差来估计当前预测的不确定性
                        start_idx = max(0, t - window_size + 1)
                        # 误差索引需要偏移，因为误差比预测值少config.predict_day个点
                        error_start_idx = max(0, start_idx - config.predict_day)
                        error_end_idx = max(0, t - config.predict_day + 1)

                        if error_end_idx > error_start_idx:
                            window_errors = error_i[error_start_idx:error_end_idx]
                            window_len = len(window_errors)

                            if window_len < 5:
                                # 如果窗口内样本太少，使用全局标准差
                                error_std = global_error_std
                            else:
                                error_std = np.std(window_errors, ddof=0)

                            # 应用标准误差调整（如果启用）
                            if config.use_standard_error and window_len > 0:
                                error_std = error_std / np.sqrt(window_len)
                        else:
                            # 没有可用的误差数据，使用全局标准差
                            error_std = global_error_std
                            if config.use_standard_error and error.shape[0] > 0:
                                error_std = error_std / np.sqrt(error.shape[0])

                        # 计算置信半宽，并应用缩放因子
                        half_width = confidence_z * error_std * config.confidence_interval_scale
                        confidence_upper[t] = predict_data[t, i] + half_width
                        confidence_lower[t] = predict_data[t, i] - half_width
                else:
                    # 没有误差数据，置信区间为零宽度
                    confidence_upper = predict_data[:, i]
                    confidence_lower = predict_data[:, i]

                confidence_intervals.append((confidence_lower, confidence_upper))
                logger.info(f"Confidence interval for {label_name[i]}: average width = {np.mean(confidence_upper - confidence_lower):.4f}")
        else:
            # 简单置信区间计算（全局标准差）
            logger.info("Using simple confidence intervals (global standard deviation)")
            for i in range(label_column_num):
                n_samples = len(predict_data[:, i])
                # 使用前面计算的调整误差（adjusted_error）和置信水平z值
                # adjusted_error 已经根据 use_standard_error 调整过
                half_width = confidence_z * adjusted_error[i] * config.confidence_interval_scale
                confidence_upper = predict_data[:, i] + half_width
                confidence_lower = predict_data[:, i] - half_width
                confidence_intervals.append((confidence_lower, confidence_upper))
                logger.info(f"Confidence interval for {label_name[i]}: width = {2*half_width:.4f} (global)")

        for i in range(label_column_num):
            plt.figure(i+1, figsize=(12, 6))                     # 预测数据绘制，设置图形大小
            plt.plot(label_X, label_data[:, i], label='真实值', linewidth=2, alpha=0.7)
            plt.plot(predict_X, predict_data[:, i], label='预测值', linewidth=2, alpha=0.7)
            # 添加置信区间区域
            confidence_lower, confidence_upper = confidence_intervals[i]
            plt.fill_between(predict_X,
                             confidence_lower,
                             confidence_upper,
                             alpha=0.2, color='green', label=f'{int(config.confidence_level*100)}%置信区间')
            plt.title(f"股票{label_name[i]}价格预测", fontsize=14)
            plt.xlabel('时间（天）', fontsize=12)
            plt.ylabel('价格（元）', fontsize=12)
            plt.legend()
            plt.grid(True, alpha=0.3)  # 添加网格，透明度0.3
            # 设置坐标轴字体大小
            plt.tick_params(axis='both', which='major', labelsize=10)
            logger.info("The predicted stock {} for the next {} day(s) is: ".format(label_name[i], config.predict_day) +
                  str(np.squeeze(predict_data[-config.predict_day:, i])))
            if config.do_figure_save:
                plt.savefig(config.figure_save_path+"{}predict_{}_with_{}.png".format(config.continue_flag, label_name[i], config.used_frame), dpi=300, bbox_inches='tight')

        plt.show()

import shutil  # 用于文件复制

def backup_model(config):
    """训练前备份模型为a和b两个副本"""
    original_model_path = os.path.join(config.model_save_path, config.model_name)
    # 若原始模型存在，则备份
    if os.path.exists(original_model_path):
        # 副本a路径（用于增量训练）
        model_a_path = os.path.join(config.model_save_path, "model_a" + config.model_postfix[config.used_frame])
        # 副本b路径（用于恢复）
        model_b_path = os.path.join(config.model_save_path, "model_b" + config.model_postfix[config.used_frame])
        # 复制原始模型到a和b
        shutil.copy2(original_model_path, model_a_path)
        shutil.copy2(original_model_path, model_b_path)
        print(f"已备份模型到 {model_a_path} 和 {model_b_path}")

def restore_model(config):
    """用副本b覆盖副本a，恢复原始模型"""
    original_model_path = os.path.join(config.model_save_path, config.model_name)
    model_b_path = os.path.join(config.model_save_path, "model_b" + config.model_postfix[config.used_frame])
    if os.path.exists(model_b_path):
        shutil.copy2(model_b_path, original_model_path)
        print(f"已用副本b恢复模型到 {original_model_path}")

def main(config):
    logger = load_logger(config)
    try:
        np.random.seed(config.random_seed)  # 设置随机种子，保证可复现
        data_gainer = Data(config)

        if config.do_train:
            train_X, valid_X, train_Y, valid_Y = data_gainer.get_train_and_valid_data()
            train(config, logger, [train_X, train_Y, valid_X, valid_Y])

        if config.do_predict:
            test_X, test_Y = data_gainer.get_test_data(return_label_data=True)
            pred_result = predict(config, test_X)       # 这里输出的是未还原的归一化预测数据
            draw(config, data_gainer, logger, pred_result)
    except Exception:
        logger.error("Run Error", exc_info=True)


if __name__=="__main__":
    import argparse
    # argparse方便于命令行下输入参数，可以根据需要增加更多
    parser = argparse.ArgumentParser()
    # parser.add_argument("-t", "--do_train", default=False, type=bool, help="whether to train")
    # parser.add_argument("-p", "--do_predict", default=True, type=bool, help="whether to train")
    # parser.add_argument("-b", "--batch_size", default=64, type=int, help="batch size")
    # parser.add_argument("-e", "--epoch", default=20, type=int, help="epochs num")
    args = parser.parse_args()

    con = Config()
    for key in dir(args):               # dir(args) 函数获得args所有的属性
        if not key.startswith("_"):     # 去掉 args 自带属性，比如__name__等
            setattr(con, key, getattr(args, key))   # 将属性值赋给Config

    main(con)
