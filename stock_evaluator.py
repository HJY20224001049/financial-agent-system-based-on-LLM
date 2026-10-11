# -*- coding: UTF-8 -*-
"""
评估指标和对比报告生成
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, mean_absolute_percentage_error, precision_score, recall_score, f1_score


def set_chinese_font():
    """设置中文字体支持，确保图表中的中文正常显示"""
    try:
        import matplotlib
        import platform
        import os as os_module

        system = platform.system()

        if system == 'Windows':
            # Windows系统字体路径
            font_paths = [
                'C:/Windows/Fonts/msyh.ttc',    # 微软雅黑
                'C:/Windows/Fonts/msyhbd.ttc',  # 微软雅黑粗体
                'C:/Windows/Fonts/simhei.ttf',  # 黑体
                'C:/Windows/Fonts/simkai.ttf',  # 楷体
                'C:/Windows/Fonts/simsun.ttc',  # 宋体
                'C:/Windows/Fonts/simfang.ttf', # 仿宋
                'C:/Windows/Fonts/simli.ttf',   # 隶书
            ]
        elif system == 'Linux':
            # Linux系统字体路径
            font_paths = [
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
                '/usr/share/fonts/truetype/arphic/uming.ttc',
                '/usr/share/fonts/truetype/arphic/ukai.ttc',
            ]
        else:  # macOS
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/STHeiti Medium.ttc',
                '/Library/Fonts/Arial Unicode.ttf',
                '/System/Library/Fonts/Hiragino Sans GB.ttc',
            ]

        # 尝试添加可用的中文字体
        font_added = False
        font_name = None
        for font_path in font_paths:
            if os_module.path.exists(font_path):
                try:
                    # 清除字体缓存，确保新字体能加载
                    matplotlib.font_manager._rebuild()
                    matplotlib.font_manager.fontManager.addfont(font_path)
                    font_prop = matplotlib.font_manager.FontProperties(fname=font_path)
                    font_name = font_prop.get_name()
                    plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams['font.sans-serif']
                    font_added = True
                    print(f"已添加中文字体: {font_name} (路径: {font_path})")
                    break
                except Exception as e:
                    print(f"添加字体失败 {font_path}: {e}")

        # 如果未添加成功，使用已知的字体名称
        if not font_added:
            # 尝试直接设置常见中文字体名称
            if system == 'Windows':
                fallback_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong']
            elif system == 'Linux':
                fallback_fonts = ['WenQuanYi Micro Hei', 'WenQuanYi Zen Hei', 'DejaVu Sans']
            else:  # macOS
                fallback_fonts = ['PingFang SC', 'Hiragino Sans GB', 'STHeiti']

            # 检查系统中有哪些字体可用
            available_fonts = set([f.name for f in matplotlib.font_manager.fontManager.ttflist])
            for font in fallback_fonts:
                if font in available_fonts:
                    plt.rcParams['font.sans-serif'] = [font] + plt.rcParams['font.sans-serif']
                    font_added = True
                    print(f"使用系统中文字体: {font}")
                    break

        # 如果仍然未添加成功，使用默认字体列表
        if not font_added:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
            print("使用默认字体列表")

        plt.rcParams['axes.unicode_minus'] = False
        print("中文字体设置完成")

        # 验证字体设置
        current_font = plt.rcParams['font.sans-serif'][0]
        print(f"当前使用字体: {current_font}")

    except Exception as e:
        print(f"中文字体设置失败: {e}")
        # 设置英文字体避免中文乱码
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        print("已回退到英文字体")


def calculate_metrics(y_true, y_pred):
    """计算回归评估指标"""
    metrics = {}

    # 确保形状一致
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    # 整体指标
    metrics['mse'] = mean_squared_error(y_true, y_pred)
    metrics['rmse'] = np.sqrt(metrics['mse'])
    metrics['mae'] = mean_absolute_error(y_true, y_pred)
    metrics['r2'] = r2_score(y_true, y_pred)

    # 计算MAPE（平均绝对百分比误差），处理可能的零值
    try:
        metrics['mape'] = mean_absolute_percentage_error(y_true, y_pred) * 100  # 转换为百分比
    except:
        # 自定义MAPE计算，避免除零
        epsilon = 1e-10
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + epsilon))) * 100
        metrics['mape'] = mape

    # 按输出维度计算指标（多输出回归）
    if len(y_true.shape) > 1 and y_true.shape[1] > 1:
        for i in range(y_true.shape[1]):
            metrics[f'mse_output_{i}'] = mean_squared_error(y_true[:, i], y_pred[:, i])
            metrics[f'rmse_output_{i}'] = np.sqrt(metrics[f'mse_output_{i}'])
            metrics[f'mae_output_{i}'] = mean_absolute_error(y_true[:, i], y_pred[:, i])
            metrics[f'r2_output_{i}'] = r2_score(y_true[:, i], y_pred[:, i])
            # 计算每个输出维度的MAPE
            try:
                metrics[f'mape_output_{i}'] = mean_absolute_percentage_error(y_true[:, i], y_pred[:, i]) * 100
            except:
                epsilon = 1e-10
                mape_i = np.mean(np.abs((y_true[:, i] - y_pred[:, i]) / (y_true[:, i] + epsilon))) * 100
                metrics[f'mape_output_{i}'] = mape_i

    # 添加多样化指标：夏普比率、波动率、最大回撤、方向准确性、F1等
    # 确保数据是二维的
    if len(y_true.shape) == 1:
        y_true = y_true.reshape(-1, 1)
        y_pred = y_pred.reshape(-1, 1)

    n_samples, n_outputs = y_true.shape

    # 对每个输出维度计算金融指标和分类指标
    for i in range(n_outputs):
        y_true_i = y_true[:, i]
        y_pred_i = y_pred[:, i]

        # 1. 计算收益率序列（对数收益率）
        # 假设样本按时间顺序排列
        eps = 1e-10
        returns_true = np.diff(np.log(y_true_i + eps))
        returns_pred = np.diff(np.log(y_pred_i + eps))

        if len(returns_true) > 1 and len(returns_pred) > 1:
            # 2. 夏普比率（年化，假设日数据，无风险利率为0）
            mean_return_true = np.mean(returns_true)
            std_return_true = np.std(returns_true)
            sharpe_true = np.sqrt(252) * mean_return_true / std_return_true if std_return_true > 0 else 0

            mean_return_pred = np.mean(returns_pred)
            std_return_pred = np.std(returns_pred)
            sharpe_pred = np.sqrt(252) * mean_return_pred / std_return_pred if std_return_pred > 0 else 0

            metrics[f'sharpe_true_output_{i}'] = sharpe_true
            metrics[f'sharpe_pred_output_{i}'] = sharpe_pred

            # 3. 波动率（年化标准差）
            volatility_true = std_return_true * np.sqrt(252)
            volatility_pred = std_return_pred * np.sqrt(252)
            metrics[f'volatility_true_output_{i}'] = volatility_true
            metrics[f'volatility_pred_output_{i}'] = volatility_pred

            # 4. 最大回撤
            # 计算累积收益率
            cum_returns_true = np.cumprod(1 + returns_true) - 1
            cum_returns_pred = np.cumprod(1 + returns_pred) - 1

            def max_drawdown(cum_returns):
                peak = np.maximum.accumulate(cum_returns)
                drawdown = (peak - cum_returns) / (peak + eps)
                return np.max(drawdown) if len(drawdown) > 0 else 0

            mdd_true = max_drawdown(cum_returns_true)
            mdd_pred = max_drawdown(cum_returns_pred)
            metrics[f'max_drawdown_true_output_{i}'] = mdd_true
            metrics[f'max_drawdown_pred_output_{i}'] = mdd_pred

            # 5. 方向准确性
            # 计算收益率方向（上涨为1，下跌为0）
            direction_true = (returns_true > 0).astype(int)
            direction_pred = (returns_pred > 0).astype(int)

            accuracy = np.mean(direction_true == direction_pred)
            metrics[f'directional_accuracy_output_{i}'] = accuracy

            # 6. 分类指标：精确率、召回率、F1
            # 使用全局导入的precision_score, recall_score, f1_score
            try:
                precision = precision_score(direction_true, direction_pred, zero_division=0)
                recall = recall_score(direction_true, direction_pred, zero_division=0)
                f1 = f1_score(direction_true, direction_pred, zero_division=0)
                metrics[f'precision_output_{i}'] = precision
                metrics[f'recall_output_{i}'] = recall
                metrics[f'f1_output_{i}'] = f1
            except Exception as e:
                metrics[f'precision_output_{i}'] = 0
                metrics[f'recall_output_{i}'] = 0
                metrics[f'f1_output_{i}'] = 0

    # 整体指标（平均各输出维度）
    if n_outputs > 1:
        # 夏普比率平均
        sharpe_pred_list = [metrics.get(f'sharpe_pred_output_{i}', 0) for i in range(n_outputs)]
        metrics['sharpe_pred_avg'] = np.mean(sharpe_pred_list)
        sharpe_true_list = [metrics.get(f'sharpe_true_output_{i}', 0) for i in range(n_outputs)]
        metrics['sharpe_true_avg'] = np.mean(sharpe_true_list)

        # 波动率平均
        vol_pred_list = [metrics.get(f'volatility_pred_output_{i}', 0) for i in range(n_outputs)]
        metrics['volatility_pred_avg'] = np.mean(vol_pred_list)
        vol_true_list = [metrics.get(f'volatility_true_output_{i}', 0) for i in range(n_outputs)]
        metrics['volatility_true_avg'] = np.mean(vol_true_list)

        # 最大回撤平均
        mdd_pred_list = [metrics.get(f'max_drawdown_pred_output_{i}', 0) for i in range(n_outputs)]
        metrics['max_drawdown_pred_avg'] = np.mean(mdd_pred_list)
        mdd_true_list = [metrics.get(f'max_drawdown_true_output_{i}', 0) for i in range(n_outputs)]
        metrics['max_drawdown_true_avg'] = np.mean(mdd_true_list)

        # 方向准确性平均
        da_list = [metrics.get(f'directional_accuracy_output_{i}', 0) for i in range(n_outputs)]
        metrics['directional_accuracy_avg'] = np.mean(da_list)

        # F1平均
        f1_list = [metrics.get(f'f1_output_{i}', 0) for i in range(n_outputs)]
        metrics['f1_avg'] = np.mean(f1_list)
        precision_list = [metrics.get(f'precision_output_{i}', 0) for i in range(n_outputs)]
        metrics['precision_avg'] = np.mean(precision_list)
        recall_list = [metrics.get(f'recall_output_{i}', 0) for i in range(n_outputs)]
        metrics['recall_avg'] = np.mean(recall_list)
    else:
        # 只有一个输出维度，复制到整体指标
        if 'sharpe_pred_output_0' in metrics:
            metrics['sharpe_pred_avg'] = metrics['sharpe_pred_output_0']
            metrics['sharpe_true_avg'] = metrics['sharpe_true_output_0']
            metrics['volatility_pred_avg'] = metrics['volatility_pred_output_0']
            metrics['volatility_true_avg'] = metrics['volatility_true_output_0']
            metrics['max_drawdown_pred_avg'] = metrics['max_drawdown_pred_output_0']
            metrics['max_drawdown_true_avg'] = metrics['max_drawdown_true_output_0']
            metrics['directional_accuracy_avg'] = metrics['directional_accuracy_output_0']
            metrics['f1_avg'] = metrics.get('f1_output_0', 0)
            metrics['precision_avg'] = metrics.get('precision_output_0', 0)
            metrics['recall_avg'] = metrics.get('recall_output_0', 0)

    return metrics


def print_metrics(metrics, model_name=""):
    """打印评估指标"""
    print(f"\n{model_name} 评估结果:")
    print("=" * 50)
    print(f"MSE:   {metrics['mse']:.6f}")
    print(f"RMSE:  {metrics['rmse']:.6f}")
    print(f"MAE:   {metrics['mae']:.6f}")
    print(f"R2:    {metrics['r2']:.6f}")
    if 'mape' in metrics:
        print(f"MAPE:  {metrics['mape']:.2f}%")

    # 打印各输出维度的指标
    for key in metrics:
        if key.startswith('mse_output_'):
            idx = key.split('_')[-1]
            print(f"\n输出维度 {idx}:")
            print(f"  MSE:   {metrics[f'mse_output_{idx}']:.6f}")
            print(f"  RMSE:  {metrics[f'rmse_output_{idx}']:.6f}")
            print(f"  MAE:   {metrics[f'mae_output_{idx}']:.6f}")
            print(f"  R2:    {metrics[f'r2_output_{idx}']:.6f}")
            if f'mape_output_{idx}' in metrics:
                print(f"  MAPE:  {metrics[f'mape_output_{idx}']:.2f}%")

    # 打印多样化指标（整体平均）
    print("\n" + "=" * 50)
    print("多样化指标（整体平均）:")
    if 'sharpe_pred_avg' in metrics:
        print(f"夏普比率（预测）: {metrics['sharpe_pred_avg']:.4f}")
    if 'sharpe_true_avg' in metrics:
        print(f"夏普比率（真实）: {metrics['sharpe_true_avg']:.4f}")
    if 'volatility_pred_avg' in metrics:
        print(f"波动率（预测）: {metrics['volatility_pred_avg']:.4f}")
    if 'volatility_true_avg' in metrics:
        print(f"波动率（真实）: {metrics['volatility_true_avg']:.4f}")
    if 'max_drawdown_pred_avg' in metrics:
        print(f"最大回撤（预测）: {metrics['max_drawdown_pred_avg']:.4f}")
    if 'max_drawdown_true_avg' in metrics:
        print(f"最大回撤（真实）: {metrics['max_drawdown_true_avg']:.4f}")
    if 'directional_accuracy_avg' in metrics:
        print(f"方向准确性: {metrics['directional_accuracy_avg']:.4f}")
    if 'f1_avg' in metrics:
        print(f"F1分数: {metrics['f1_avg']:.4f}")
    if 'precision_avg' in metrics:
        print(f"精确率: {metrics['precision_avg']:.4f}")
    if 'recall_avg' in metrics:
        print(f"召回率: {metrics['recall_avg']:.4f}")

    # 打印各输出维度的多样化指标（可选）
    # 如果需要可以取消注释
    # for key in metrics:
    #     if key.startswith('sharpe_pred_output_'):
    #         idx = key.split('_')[-1]
    #         print(f"\n输出维度 {idx} 多样化指标:")
    #         print(f"  夏普比率（预测）: {metrics[f'sharpe_pred_output_{idx}']:.4f}")
    #         print(f"  波动率（预测）: {metrics[f'volatility_pred_output_{idx}']:.4f}")
    #         print(f"  最大回撤（预测）: {metrics[f'max_drawdown_pred_output_{idx}']:.4f}")
    #         print(f"  方向准确性: {metrics[f'directional_accuracy_output_{idx}']:.4f}")
    #         if f'f1_output_{idx}' in metrics:
    #             print(f"  F1分数: {metrics[f'f1_output_{idx}']:.4f}")


def save_metrics(metrics, model_name, save_dir):
    """保存评估指标到文件"""
    os.makedirs(save_dir, exist_ok=True)

    # 保存为文本文件
    txt_path = os.path.join(save_dir, f"{model_name}_metrics.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"{model_name} 评估指标\n")
        f.write("=" * 60 + "\n\n")

        f.write("整体指标:\n")
        f.write(f"MSE:   {metrics['mse']:.6f}\n")
        f.write(f"RMSE:  {metrics['rmse']:.6f}\n")
        f.write(f"MAE:   {metrics['mae']:.6f}\n")
        f.write(f"R2:    {metrics['r2']:.6f}\n")
        if 'mape' in metrics:
            f.write(f"MAPE:  {metrics['mape']:.2f}%\n")
        f.write("\n")

        # 多样化指标（整体平均）
        f.write("多样化指标（整体平均）:\n")
        if 'sharpe_pred_avg' in metrics:
            f.write(f"夏普比率（预测）: {metrics['sharpe_pred_avg']:.6f}\n")
        if 'sharpe_true_avg' in metrics:
            f.write(f"夏普比率（真实）: {metrics['sharpe_true_avg']:.6f}\n")
        if 'volatility_pred_avg' in metrics:
            f.write(f"波动率（预测）: {metrics['volatility_pred_avg']:.6f}\n")
        if 'volatility_true_avg' in metrics:
            f.write(f"波动率（真实）: {metrics['volatility_true_avg']:.6f}\n")
        if 'max_drawdown_pred_avg' in metrics:
            f.write(f"最大回撤（预测）: {metrics['max_drawdown_pred_avg']:.6f}\n")
        if 'max_drawdown_true_avg' in metrics:
            f.write(f"最大回撤（真实）: {metrics['max_drawdown_true_avg']:.6f}\n")
        if 'directional_accuracy_avg' in metrics:
            f.write(f"方向准确性: {metrics['directional_accuracy_avg']:.6f}\n")
        if 'f1_avg' in metrics:
            f.write(f"F1分数: {metrics['f1_avg']:.6f}\n")
        if 'precision_avg' in metrics:
            f.write(f"精确率: {metrics['precision_avg']:.6f}\n")
        if 'recall_avg' in metrics:
            f.write(f"召回率: {metrics['recall_avg']:.6f}\n")
        f.write("\n")

        # 各输出维度指标
        for key in sorted(metrics.keys()):
            if key.startswith('mse_output_'):
                idx = key.split('_')[-1]
                f.write(f"输出维度 {idx}:\n")
                f.write(f"  MSE:   {metrics[f'mse_output_{idx}']:.6f}\n")
                f.write(f"  RMSE:  {metrics[f'rmse_output_{idx}']:.6f}\n")
                f.write(f"  MAE:   {metrics[f'mae_output_{idx}']:.6f}\n")
                f.write(f"  R2:    {metrics[f'r2_output_{idx}']:.6f}\n")
                if f'mape_output_{idx}' in metrics:
                    f.write(f"  MAPE:  {metrics[f'mape_output_{idx}']:.2f}%\n")
                # 输出维度的多样化指标
                if f'sharpe_pred_output_{idx}' in metrics:
                    f.write(f"  夏普比率（预测）: {metrics[f'sharpe_pred_output_{idx}']:.6f}\n")
                if f'volatility_pred_output_{idx}' in metrics:
                    f.write(f"  波动率（预测）: {metrics[f'volatility_pred_output_{idx}']:.6f}\n")
                if f'max_drawdown_pred_output_{idx}' in metrics:
                    f.write(f"  最大回撤（预测）: {metrics[f'max_drawdown_pred_output_{idx}']:.6f}\n")
                if f'directional_accuracy_output_{idx}' in metrics:
                    f.write(f"  方向准确性: {metrics[f'directional_accuracy_output_{idx}']:.6f}\n")
                if f'f1_output_{idx}' in metrics:
                    f.write(f"  F1分数: {metrics[f'f1_output_{idx}']:.6f}\n")
                if f'precision_output_{idx}' in metrics:
                    f.write(f"  精确率: {metrics[f'precision_output_{idx}']:.6f}\n")
                if f'recall_output_{idx}' in metrics:
                    f.write(f"  召回率: {metrics[f'recall_output_{idx}']:.6f}\n")
                f.write("\n")

    print(f"指标已保存至: {txt_path}")
    return txt_path


def plot_predictions(y_true, y_pred, model_name, save_dir, feature_names=None):
    """绘制预测结果对比图"""
    os.makedirs(save_dir, exist_ok=True)

    # 设置中文字体支持，确保图表中的中文正常显示
    try:
        import matplotlib
        import platform
        import os as os_module

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
            if os_module.path.exists(font_path):
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

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    # 如果有多维输出，分别绘制
    if len(y_true.shape) == 1:
        y_true = y_true.reshape(-1, 1)
        y_pred = y_pred.reshape(-1, 1)

    n_outputs = y_true.shape[1]

    for i in range(n_outputs):
        plt.figure(figsize=(12, 6))

        # 绘制真实值和预测值
        plt.plot(y_true[:, i], label='真实值', alpha=0.7, linewidth=2)
        plt.plot(y_pred[:, i], label='预测值', alpha=0.7, linewidth=2)

        # 计算预测误差
        pred_errors = y_true[:, i] - y_pred[:, i]
        n_samples = len(pred_errors)
        # 动态计算窗口大小：样本数的10%，但范围在10到50之间
        window_size = max(10, min(50, int(n_samples * 0.1)))
        confidence_upper = np.zeros(n_samples)
        confidence_lower = np.zeros(n_samples)
        z_score = 1.96  # 95%置信水平

        # 计算全局误差标准差作为后备
        global_error_std = np.std(pred_errors, ddof=0) if len(pred_errors) > 0 else 0.0

        for t in range(n_samples):
            # 计算窗口内的误差标准差
            start_idx = max(0, t - window_size + 1)
            window_errors = pred_errors[start_idx:t+1]
            window_len = len(window_errors)

            if window_len < 5:
                # 如果窗口内样本太少，使用全局标准差
                error_std = global_error_std
            else:
                error_std = np.std(window_errors, ddof=0)

            # 计算置信半宽
            half_width = z_score * error_std
            confidence_upper[t] = y_pred[t, i] + half_width
            confidence_lower[t] = y_pred[t, i] - half_width

        # 绘制置信区间区域
        plt.fill_between(range(n_samples),
                         confidence_lower,
                         confidence_upper,
                         alpha=0.2, color='green', label='95%置信区间')

        feature_name = feature_names[i] if feature_names else f'输出维度 {i}'
        plt.title(f'{model_name} - {feature_name}预测对比', fontsize=14)
        plt.xlabel('样本索引', fontsize=12)
        plt.ylabel('值', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)

        # 保存图像
        fig_path = os.path.join(save_dir, f"{model_name}_output_{i}.png")
        plt.savefig(fig_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"预测对比图已保存至: {fig_path}")


def generate_comparison_report(results, save_dir):
    """生成模型对比报告"""
    os.makedirs(save_dir, exist_ok=True)

    # 提取主要指标
    comparison_data = []
    for model_name, metrics in results.items():
        row = {'Model': model_name}
        row['MSE'] = metrics.get('mse', np.nan)
        row['RMSE'] = metrics.get('rmse', np.nan)
        row['MAE'] = metrics.get('mae', np.nan)
        row['R2'] = metrics.get('r2', np.nan)
        row['MAPE'] = metrics.get('mape', np.nan)
        # 多样化指标
        row['Sharpe_Pred'] = metrics.get('sharpe_pred_avg', np.nan)
        row['Sharpe_True'] = metrics.get('sharpe_true_avg', np.nan)
        row['Volatility_Pred'] = metrics.get('volatility_pred_avg', np.nan)
        row['Volatility_True'] = metrics.get('volatility_true_avg', np.nan)
        row['MaxDrawdown_Pred'] = metrics.get('max_drawdown_pred_avg', np.nan)
        row['MaxDrawdown_True'] = metrics.get('max_drawdown_true_avg', np.nan)
        row['Directional_Accuracy'] = metrics.get('directional_accuracy_avg', np.nan)
        row['F1'] = metrics.get('f1_avg', np.nan)
        row['Precision'] = metrics.get('precision_avg', np.nan)
        row['Recall'] = metrics.get('recall_avg', np.nan)
        comparison_data.append(row)

    df = pd.DataFrame(comparison_data)

    # 按RMSE排序
    df_sorted = df.sort_values('RMSE')

    # 保存CSV
    csv_path = os.path.join(save_dir, "model_comparison.csv")
    df_sorted.to_csv(csv_path, index=False, encoding='utf-8-sig')

    # 生成Markdown报告
    md_path = os.path.join(save_dir, "comparison_report.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# 股票预测模型对比实验报告\n\n")
        f.write("## 实验概述\n")
        f.write("- 任务: 股票价格多步预测\n")
        f.write("- 预测目标: 最低价和最高价\n")
        f.write("- 数据特征: 开盘价、收盘价、最低价、最高价、成交量、成交额、涨跌幅\n")
        f.write(f"- 模型数量: {len(results)}\n")
        f.write("- 评估指标: MSE, RMSE, MAE, R2\n\n")

        f.write("## 模型性能对比\n\n")
        f.write(df_sorted.to_markdown(index=False) + "\n\n")

        f.write("## 性能分析\n\n")
        # 定义指标及其优化方向（minimize 或 maximize）
        metric_config = [
            ('MSE', 'minimize'),
            ('RMSE', 'minimize'),
            ('MAE', 'minimize'),
            ('MAPE', 'minimize'),
            ('R2', 'maximize'),
            ('Sharpe_Pred', 'maximize'),
            ('Sharpe_True', 'maximize'),
            ('Volatility_Pred', 'minimize'),
            ('Volatility_True', 'minimize'),
            ('MaxDrawdown_Pred', 'minimize'),
            ('MaxDrawdown_True', 'minimize'),
            ('Directional_Accuracy', 'maximize'),
            ('F1', 'maximize'),
            ('Precision', 'maximize'),
            ('Recall', 'maximize')
        ]

        for metric, direction in metric_config:
            if metric in df_sorted.columns:
                if direction == 'minimize':
                    best_idx = df_sorted[metric].idxmin()
                else:
                    best_idx = df_sorted[metric].idxmax()
                best_model = df_sorted.loc[best_idx]
                best_value = best_model[metric]
                best_name = best_model['Model']

                if metric == 'R2':
                    f.write(f"1. **{metric}指标**: {best_name}表现最佳，达到{best_value:.4f}（越接近1越好）\n")
                elif metric == 'MAPE':
                    f.write(f"1. **{metric}指标**: {best_name}表现最佳，达到{best_value:.2f}%（越低越好）\n")
                elif metric.startswith('Sharpe'):
                    f.write(f"1. **{metric}指标**: {best_name}表现最佳，达到{best_value:.4f}（越高越好）\n")
                elif metric.startswith('Volatility') or metric.startswith('MaxDrawdown'):
                    f.write(f"1. **{metric}指标**: {best_name}表现最佳，达到{best_value:.4f}（越低越好）\n")
                elif metric in ['Directional_Accuracy', 'F1', 'Precision', 'Recall']:
                    f.write(f"1. **{metric}指标**: {best_name}表现最佳，达到{best_value:.4f}（越高越好）\n")
                else:
                    f.write(f"1. **{metric}指标**: {best_name}表现最佳，达到{best_value:.4f}（越低越好）\n")

        f.write("\n## 结论\n")
        f.write("综合各评估指标，可以得出以下结论:\n")
        f.write("1. 整体性能最佳的模型是 **{}**（综合RMSE和MAE）\n".format(df_sorted.iloc[0]['Model']))
        f.write("2. 解释性最佳的模型是 **{}**（R2最高）\n".format(df_sorted.loc[df_sorted['R2'].idxmax()]['Model']))

        if 'LSTM' in results:
            lstm_rmse = df_sorted[df_sorted['Model'] == 'LSTM']['RMSE'].values[0]
            best_rmse = df_sorted.iloc[0]['RMSE']
            improvement = (lstm_rmse - best_rmse) / lstm_rmse * 100
            f.write(f"3. 相比基准LSTM模型，最佳模型提升了{improvement:.1f}%的RMSE性能\n")

    print(f"\n对比报告已保存至:")
    print(f"  CSV文件: {csv_path}")
    print(f"  Markdown报告: {md_path}")

    # 绘制对比柱状图
    plot_comparison_bars(df_sorted, save_dir)

    return df_sorted


def plot_comparison_bars(df, save_dir):
    """绘制模型对比柱状图"""
    # 设置中文字体支持，确保图表中的中文正常显示
    try:
        import matplotlib
        import platform
        import os as os_module

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
            if os_module.path.exists(font_path):
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

    models = df['Model'].values
    # 确定可用的指标列
    possible_metrics = ['MSE', 'RMSE', 'MAE', 'MAPE', 'R2',
                        'Sharpe_Pred', 'Sharpe_True', 'Volatility_Pred', 'Volatility_True',
                        'MaxDrawdown_Pred', 'MaxDrawdown_True', 'Directional_Accuracy',
                        'F1', 'Precision', 'Recall']
    available_metrics = []
    for metric in possible_metrics:
        if metric in df.columns:
            available_metrics.append(metric)

    if not available_metrics:
        print("警告: 没有可用的指标列，跳过绘制对比柱状图")
        return

    metrics = available_metrics
    n_metrics = len(metrics)
    fig, axes = plt.subplots(1, n_metrics, figsize=(6*n_metrics, 6))
    if n_metrics == 1:
        axes = [axes]
    else:
        axes = axes.flatten()

    for idx, metric in enumerate(metrics):
        ax = axes[idx]
        values = df[metric].values

        # 判断指标优化方向
        if metric in ['R2', 'Sharpe_Pred', 'Sharpe_True', 'Directional_Accuracy', 'F1', 'Precision', 'Recall']:
            # 越大越好，用绿色标出最大值
            colors = ['green' if v == np.nanmax(values) else 'lightblue' for v in values]
            ax.set_title(f'{metric}对比（越大越好）')
        else:
            # 越小越好，用红色标出最小值
            colors = ['red' if v == np.nanmin(values) else 'lightblue' for v in values]
            ax.set_title(f'{metric}对比（越小越好）')

        bars = ax.bar(range(len(models)), values, color=colors)
        ax.set_xlabel('模型')
        ax.set_ylabel(metric)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(models, rotation=45, ha='right')
        ax.grid(True, alpha=0.3)

        # 在柱子上方添加数值
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.4f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    fig_path = os.path.join(save_dir, "stock_compare.png")
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"对比柱状图已保存至: {fig_path}")