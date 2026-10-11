# -*- coding: UTF-8 -*-
"""
测试对比实验组件
"""

import sys
import os
sys.path.insert(0, '.')

from stock_comparison import Config, StockDataProcessor
from stock_models import LSTMModel, TransformerModel, SVMModel, RandomForestModel, DecisionTreeModel, XGBoostModel
from stock_evaluator import calculate_metrics
import numpy as np

def test_data_processor():
    print("测试数据处理器...")
    config = Config()
    config.debug_mode = True
    config.debug_num = 1000  # 使用少量数据测试

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

    return processor

def test_models_initialization():
    print("\n测试模型初始化...")
    config = Config()

    # LSTM
    lstm = LSTMModel(config)
    print(f"LSTM模型参数数量: {sum(p.numel() for p in lstm.parameters())}")

    # Transformer
    transformer = TransformerModel(config)
    print(f"Transformer模型参数数量: {sum(p.numel() for p in transformer.parameters())}")

    # SVM
    svm = SVMModel(config)
    print("SVM模型初始化成功")

    # 随机森林
    rf = RandomForestModel(config)
    print("随机森林模型初始化成功")

    # XGBoost
    xgb = XGBoostModel(config)
    print("XGBoost模型初始化成功")

    # 决策树
    dt = DecisionTreeModel(config)
    print("决策树模型初始化成功")

    return True

def test_metrics():
    print("\n测试评估指标计算...")

    # 生成模拟数据
    y_true = np.random.randn(100, 2)
    y_pred = y_true + np.random.randn(100, 2) * 0.1

    metrics = calculate_metrics(y_true, y_pred)

    print("评估指标:")
    print(f"  MSE: {metrics['mse']:.6f}")
    print(f"  RMSE: {metrics['rmse']:.6f}")
    print(f"  MAE: {metrics['mae']:.6f}")
    print(f"  R2: {metrics['r2']:.6f}")

    return True

def main():
    print("="*60)
    print("股票预测对比实验组件测试")
    print("="*60)

    try:
        processor = test_data_processor()
        test_models_initialization()
        test_metrics()

        print("\n" + "="*60)
        print("所有组件测试通过！")
        print("="*60)

    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)