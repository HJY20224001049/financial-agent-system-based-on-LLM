# -*- coding: UTF-8 -*-
"""
运行股票预测模型对比实验
"""

import sys
import os
# 设置临时文件夹避免中文路径问题
temp_dir = "C:/temp_joblib"
os.makedirs(temp_dir, exist_ok=True)
os.environ['JOBLIB_TEMP_FOLDER'] = temp_dir
os.environ['TMP'] = temp_dir
os.environ['TEMP'] = temp_dir

import numpy as np
import torch
from stock_comparison import Config, StockDataProcessor, load_logger
from stock_models import (
    LSTMModel, TransformerModel, SVMModel,
    RandomForestModel, DecisionTreeModel, XGBoostModel,
    train_lstm, train_transformer
)
from stock_evaluator import calculate_metrics, print_metrics, save_metrics, plot_predictions, generate_comparison_report
import warnings
warnings.filterwarnings('ignore')

def prepare_data_for_model(model_type, processor):
    """根据不同模型类型准备数据"""
    if model_type in ['lstm', 'transformer']:
        # 序列数据
        train_x, train_y, valid_x, valid_y, test_x, test_y = processor.prepare_sequences()
        return (train_x, train_y), (valid_x, valid_y), (test_x, test_y)

    elif model_type in ['svm', 'random_forest', 'decision_tree', 'xgboost']:
        # 扁平化数据
        train_x, train_y, valid_x, valid_y, test_x, test_y = processor.prepare_flattened_data()
        return (train_x, train_y), (valid_x, valid_y), (test_x, test_y)

    else:
        raise ValueError(f"未知的模型类型: {model_type}")


def train_and_evaluate_lstm(config, processor, logger, result_dir):
    """训练和评估LSTM模型"""
    print("\n" + "="*60)
    print("训练LSTM模型")
    print("="*60)

    # 准备数据
    train_data, val_data, test_data = prepare_data_for_model('lstm', processor)
    test_x, test_y = test_data

    # 训练模型
    model = train_lstm(config, train_data, val_data, logger)

    # 预测
    device = torch.device("cuda:0" if config.use_cuda and torch.cuda.is_available() else "cpu")
    model.eval()
    with torch.no_grad():
        test_x_tensor = torch.from_numpy(test_x).float().to(device)
        # LSTM需要处理序列输出
        test_pred, _ = model(test_x_tensor)
        test_pred = test_pred.cpu().numpy()

    # LSTM输出形状: [batch_size, time_step, output_size]
    # 我们只关心最后一个时间步的预测
    test_pred_last = test_pred[:, -1, :]

    # 反归一化
    test_pred_original = processor.inverse_normalize(test_pred_last, is_label=True)
    # 根据test_y的维度处理
    if len(test_y.shape) == 3:
        test_y_last = test_y[:, -1, :]
    else:
        test_y_last = test_y
    # 确保test_y_last与test_pred_last样本数一致
    if test_y_last.shape[0] != test_pred_last.shape[0]:
        print(f"警告: test_y样本数({test_y_last.shape[0]})与预测样本数({test_pred_last.shape[0]})不一致，进行截取")
        test_y_last = test_y_last[:test_pred_last.shape[0]]
    test_y_original = processor.inverse_normalize(test_y_last, is_label=True)

    # 计算指标
    metrics = calculate_metrics(test_y_original, test_pred_original)
    print_metrics(metrics, "LSTM")

    # 保存结果
    save_metrics(metrics, "LSTM", result_dir)
    plot_predictions(test_y_original, test_pred_original, "LSTM",
                     os.path.join(result_dir, "figures"),
                     feature_names=["最低价", "最高价"])

    return metrics


def train_and_evaluate_transformer(config, processor, logger, result_dir):
    """训练和评估Transformer模型"""
    print("\n" + "="*60)
    print("训练Transformer模型")
    print("="*60)

    # 准备数据
    train_data, val_data, test_data = prepare_data_for_model('transformer', processor)
    test_x, test_y = test_data

    # 训练模型
    model = train_transformer(config, train_data, val_data, logger)

    # 预测
    device = torch.device("cuda:0" if config.use_cuda and torch.cuda.is_available() else "cpu")
    model.eval()
    with torch.no_grad():
        test_x_tensor = torch.from_numpy(test_x).float().to(device)
        test_pred = model(test_x_tensor)
        test_pred = test_pred.cpu().numpy()

    # Transformer输出形状: [batch_size, output_size]
    # 反归一化
    test_pred_original = processor.inverse_normalize(test_pred, is_label=True)
    # 根据test_y的维度处理
    if len(test_y.shape) == 3:
        test_y_last = test_y[:, -1, :]
    else:
        test_y_last = test_y
    # 确保test_y_last与test_pred样本数一致
    if test_y_last.shape[0] != test_pred.shape[0]:
        print(f"警告: test_y样本数({test_y_last.shape[0]})与预测样本数({test_pred.shape[0]})不一致，进行截取")
        test_y_last = test_y_last[:test_pred.shape[0]]
    test_y_original = processor.inverse_normalize(test_y_last, is_label=True)

    # 计算指标
    metrics = calculate_metrics(test_y_original, test_pred_original)
    print_metrics(metrics, "Transformer")

    # 保存结果
    save_metrics(metrics, "Transformer", result_dir)
    plot_predictions(test_y_original, test_pred_original, "Transformer",
                     os.path.join(result_dir, "figures"),
                     feature_names=["最低价", "最高价"])

    return metrics


def train_and_evaluate_sklearn_model(model_type, config, processor, logger, result_dir):
    """训练和评估scikit-learn模型（SVM、随机森林、决策树、XGBoost）"""
    print("\n" + "="*60)
    print(f"训练{model_type}模型")
    print("="*60)

    # 准备数据
    train_data, val_data, test_data = prepare_data_for_model(model_type, processor)
    train_x, train_y = train_data
    val_x, val_y = val_data
    test_x, test_y = test_data

    # 初始化模型
    if model_type == 'svm':
        model = SVMModel(config)
    elif model_type == 'random_forest':
        model = RandomForestModel(config)
    elif model_type == 'decision_tree':
        model = DecisionTreeModel(config)
    elif model_type == 'xgboost':
        model = XGBoostModel(config)
    else:
        raise ValueError(f"未知的模型类型: {model_type}")

    # 训练模型
    model.fit(train_x, train_y, val_x, val_y)

    # 预测
    test_pred = model.predict(test_x)

    # 反归一化
    test_pred_original = processor.inverse_normalize(test_pred, is_label=True)
    test_y_original = processor.inverse_normalize(test_y, is_label=True)

    # 处理样本数不匹配问题
    if test_y_original.shape[0] != test_pred_original.shape[0]:
        print(f"警告: test_y样本数({test_y_original.shape[0]})与预测样本数({test_pred_original.shape[0]})不一致，进行截取")
        test_y_original = test_y_original[:test_pred_original.shape[0]]

    # 计算指标
    metrics = calculate_metrics(test_y_original, test_pred_original)
    print_metrics(metrics, model_type.upper())

    # 保存结果
    save_metrics(metrics, model_type.upper(), result_dir)
    plot_predictions(test_y_original, test_pred_original, model_type.upper(),
                     os.path.join(result_dir, "figures"),
                     feature_names=["最低价", "最高价"])

    # 保存模型
    model_path = os.path.join(config.model_save_path, f"{model_type}_model.pkl")
    if hasattr(model, 'save'):
        model.save(model_path)
    else:
        import pickle
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

    return metrics


def run_comparison_experiment():
    """运行完整的对比实验"""
    print("\n" + "="*80)
    print("股票预测模型对比实验")
    print("="*80)

    # 初始化配置
    config = Config()
    config.do_log_save_to_file = True

    # 初始化日志
    logger = load_logger(config)

    # 初始化数据处理器
    processor = StockDataProcessor(config)

    # 结果目录
    result_dir = config.result_save_path
    os.makedirs(os.path.join(result_dir, "figures"), exist_ok=True)

    # 存储所有模型的结果
    all_results = {}

    try:
        # 1. LSTM模型
        lstm_metrics = train_and_evaluate_lstm(config, processor, logger, result_dir)
        all_results['LSTM'] = lstm_metrics

        # 2. Transformer模型
        transformer_metrics = train_and_evaluate_transformer(config, processor, logger, result_dir)
        all_results['Transformer'] = transformer_metrics

        # 3. SVM模型
        svm_metrics = train_and_evaluate_sklearn_model('svm', config, processor, logger, result_dir)
        all_results['SVM'] = svm_metrics

        # 4. 随机森林模型
        rf_metrics = train_and_evaluate_sklearn_model('random_forest', config, processor, logger, result_dir)
        all_results['RandomForest'] = rf_metrics

        # 5. 决策树模型
        dt_metrics = train_and_evaluate_sklearn_model('decision_tree', config, processor, logger, result_dir)
        all_results['DecisionTree'] = dt_metrics

        # 6. XGBoost模型
        xgb_metrics = train_and_evaluate_sklearn_model('xgboost', config, processor, logger, result_dir)
        all_results['XGBoost'] = xgb_metrics

        # 生成对比报告
        print("\n" + "="*80)
        print("生成对比实验报告")
        print("="*80)

        df_comparison = generate_comparison_report(all_results, result_dir)

        # 打印总结
        print("\n" + "="*80)
        print("实验总结")
        print("="*80)
        print("\n模型性能排名（按RMSE升序）:")
        # 选择关键指标展示
        display_columns = ['Model', 'RMSE', 'MAE', 'R2', 'Sharpe_Pred', 'Directional_Accuracy', 'F1']
        # 只显示存在的列
        available_columns = [col for col in display_columns if col in df_comparison.columns]
        print(df_comparison[available_columns].to_string(index=False, float_format='{:.6f}'.format))

        best_model = df_comparison.iloc[0]['Model']
        best_rmse = df_comparison.iloc[0]['RMSE']
        print(f"\n最佳模型: {best_model} (RMSE: {best_rmse:.6f})")

        logger.info(f"对比实验完成，最佳模型: {best_model}")

    except Exception as e:
        logger.error(f"实验运行出错: {e}", exc_info=True)
        raise

    print("\n" + "="*80)
    print("对比实验完成！")
    print("="*80)


if __name__ == "__main__":
    run_comparison_experiment()