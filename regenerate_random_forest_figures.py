# -*- coding: UTF-8 -*-
"""
重新生成随机森林预测图像，确保中文字体正常显示
"""

import sys
import os
import numpy as np
import pickle
import matplotlib.pyplot as plt

# 添加当前目录到路径
sys.path.insert(0, '.')

from stock_comparison import Config, StockDataProcessor
from stock_models import RandomForestModel
from stock_evaluator import plot_predictions

def main():
    print("="*60)
    print("重新生成随机森林预测图像")
    print("="*60)

    # 初始化配置
    config = Config()
    config.do_log_save_to_file = False  # 不保存日志

    # 初始化数据处理器
    processor = StockDataProcessor(config)

    # 准备扁平化数据（随机森林使用扁平化数据）
    train_x, train_y, valid_x, valid_y, test_x, test_y = processor.prepare_flattened_data()

    # 加载随机森林模型
    model_path = os.path.join(config.model_save_path, "random_forest_model.pkl")
    if not os.path.exists(model_path):
        print(f"错误: 模型文件不存在: {model_path}")
        return False

    print(f"加载随机森林模型: {model_path}")
    with open(model_path, 'rb') as f:
        rf_model = pickle.load(f)

    # 创建RandomForestModel实例以包装模型
    # 注意：pickle加载的是RandomForestRegressor，而不是RandomForestModel
    # 我们需要将其包装到RandomForestModel中以便使用predict方法
    # 但RandomForestModel的predict方法直接调用self.model.predict
    # 所以我们可以直接使用加载的模型进行预测
    # 但为了兼容，我们创建一个简单的包装器
    class WrappedModel:
        def __init__(self, model):
            self.model = model
        def predict(self, X):
            return self.model.predict(X)

    wrapped_model = WrappedModel(rf_model)

    # 预测
    print("进行预测...")
    test_pred = wrapped_model.predict(test_x)

    # 反归一化
    test_pred_original = processor.inverse_normalize(test_pred, is_label=True)
    test_y_original = processor.inverse_normalize(test_y, is_label=True)

    # 处理样本数不匹配问题
    if test_y_original.shape[0] != test_pred_original.shape[0]:
        print(f"警告: test_y样本数({test_y_original.shape[0]})与预测样本数({test_pred_original.shape[0]})不一致，进行截取")
        test_y_original = test_y_original[:test_pred_original.shape[0]]

    # 绘制图像
    figures_dir = os.path.join(config.result_save_path, "figures")
    print(f"保存图像到: {figures_dir}")

    # 调用plot_predictions函数，该函数内部会设置中文字体
    plot_predictions(test_y_original, test_pred_original, "RANDOM_FOREST",
                     figures_dir, feature_names=["最低价", "最高价"])

    print("\n随机森林图像重新生成完成！")
    print("新图像已保存，现在应该可以正常显示中文。")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)