"""
测试SVM训练和评估，调试MAE/MSE计算问题
"""
import sys
sys.path.insert(0, '.')

from comparison_experiment import (
    prepare_data,
    create_tfidf_features,
    evaluate_model,
    SEED
)

import numpy as np

def test_svm():
    print("="*60)
    print("测试SVM模型（调试版）")
    print("="*60)

    # 1. 准备数据（使用少量数据）
    X_train, X_test, y_train, y_test = prepare_data()
    print(f"训练集: {len(X_train)} 条，测试集: {len(X_test)} 条")

    # 2. 创建TF-IDF特征（使用较小维度）
    print("\n创建TF-IDF特征...")
    X_train_tfidf, X_test_tfidf, tfidf = create_tfidf_features(X_train, X_test, max_features=2000)

    # 3. SVM训练
    print("\n" + "="*60)
    print("SVM模型训练和评估")
    from sklearn.svm import SVC

    # 使用小型数据子集加快测试
    sample_size = min(1000, X_train_tfidf.shape[0])
    X_train_small = X_train_tfidf[:sample_size]
    y_train_small = y_train[:sample_size]
    X_test_small = X_test_tfidf[:min(200, X_test_tfidf.shape[0])]
    y_test_small = y_test[:min(200, len(y_test))]

    print(f"使用样本数: 训练{sample_size}, 测试{len(y_test_small)}")

    svm = SVC(kernel='linear', probability=True, random_state=SEED)
    print("训练SVM...")
    svm.fit(X_train_small, y_train_small)

    print("预测...")
    y_pred = svm.predict(X_test_small)
    y_pred_proba = svm.predict_proba(X_test_small)[:, 1]

    # 详细调试信息
    print(f"\n详细调试信息:")
    print(f"y_test_small type: {type(y_test_small)}, length: {len(y_test_small)}")
    print(f"y_pred_proba type: {type(y_pred_proba)}, shape: {y_pred_proba.shape if hasattr(y_pred_proba, 'shape') else 'N/A'}")
    print(f"y_pred_proba dtype: {y_pred_proba.dtype if hasattr(y_pred_proba, 'dtype') else 'N/A'}")
    print(f"y_pred_proba[:10]: {y_pred_proba[:10]}")
    print(f"y_test_small[:10]: {y_test_small[:10]}")

    # 手动计算MAE/MSE测试
    print(f"\n手动计算测试:")
    try:
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        mae = mean_absolute_error(y_test_small, y_pred_proba)
        mse = mean_squared_error(y_test_small, y_pred_proba)
        print(f"直接计算 MAE: {mae:.6f}, MSE: {mse:.6f}")
    except Exception as e:
        print(f"直接计算错误: {e}")
        import traceback
        traceback.print_exc()

    # 调用evaluate_model
    print(f"\n调用evaluate_model:")
    metrics = evaluate_model(y_test_small, y_pred, y_pred_proba, "SVM_test")

    print(f"\n测试完成。")
    return metrics

if __name__ == '__main__':
    test_svm()