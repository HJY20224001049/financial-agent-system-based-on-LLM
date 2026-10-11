# -*- coding: UTF-8 -*-
"""
从metrics文件生成对比报告
"""
import os
import pandas as pd
import numpy as np

def parse_metrics_file(filepath):
    """解析metrics文本文件，返回指标字典"""
    metrics = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line.startswith('MSE:'):
            metrics['mse'] = float(line.split(':')[1].strip())
        elif line.startswith('RMSE:'):
            metrics['rmse'] = float(line.split(':')[1].strip())
        elif line.startswith('MAE:'):
            metrics['mae'] = float(line.split(':')[1].strip())
        elif line.startswith('R2:'):
            metrics['r2'] = float(line.split(':')[1].strip())

    return metrics

def main():
    result_dir = "./comparison_results/"
    model_files = [
        ('LSTM', 'LSTM_metrics.txt'),
        ('Transformer', 'Transformer_metrics.txt'),
        ('SVM', 'SVM_metrics.txt'),
        ('RandomForest', 'RANDOM_FOREST_metrics.txt'),
        ('XGBoost', 'XGBOOST_metrics.txt')
    ]

    all_results = {}
    for model_name, filename in model_files:
        filepath = os.path.join(result_dir, filename)
        if os.path.exists(filepath):
            metrics = parse_metrics_file(filepath)
            all_results[model_name] = metrics
            print(f"{model_name}: RMSE={metrics.get('rmse', 'N/A'):.2f}, MAE={metrics.get('mae', 'N/A'):.2f}, R2={metrics.get('r2', 'N/A'):.4f}")
        else:
            print(f"文件不存在: {filepath}")

    # 创建DataFrame
    df_data = []
    for model_name, metrics in all_results.items():
        df_data.append({
            'Model': model_name,
            'MSE': metrics.get('mse', np.nan),
            'RMSE': metrics.get('rmse', np.nan),
            'MAE': metrics.get('mae', np.nan),
            'R2': metrics.get('r2', np.nan)
        })

    df = pd.DataFrame(df_data)
    df_sorted = df.sort_values('RMSE')

    print("\n模型性能排名（按RMSE升序）:")
    print(df_sorted.to_string(index=False))

    # 保存CSV
    csv_path = os.path.join(result_dir, "model_comparison_summary.csv")
    df_sorted.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"\n对比汇总已保存至: {csv_path}")

    # 分析最佳模型
    best_rmse_model = df_sorted.iloc[0]
    best_r2_model = df_sorted.loc[df_sorted['R2'].idxmax()] if 'R2' in df_sorted.columns else None

    print(f"\n最佳RMSE模型: {best_rmse_model['Model']} (RMSE: {best_rmse_model['RMSE']:.2f})")
    if best_r2_model is not None:
        print(f"最佳R2模型: {best_r2_model['Model']} (R2: {best_r2_model['R2']:.4f})")

    # 与LSTM基准对比
    if 'LSTM' in all_results:
        lstm_rmse = df[df['Model'] == 'LSTM']['RMSE'].values[0]
        best_rmse = df_sorted.iloc[0]['RMSE']
        improvement = (lstm_rmse - best_rmse) / lstm_rmse * 100
        print(f"相比基准LSTM模型，最佳模型提升了{improvement:.1f}%的RMSE性能")

    return df_sorted

if __name__ == "__main__":
    df = main()