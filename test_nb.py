"""
测试朴素贝叶斯模型
"""
import sys
sys.path.insert(0, '.')

from comparison_experiment import (
    prepare_data,
    create_tfidf_features,
    train_naive_bayes,
    SEED
)

print("测试朴素贝叶斯模型...")
X_train, X_test, y_train, y_test = prepare_data()
print(f"训练集大小: {len(X_train)}")
print(f"测试集大小: {len(X_test)}")

# 使用较小的特征维度加快测试
X_train_tfidf, X_test_tfidf, tfidf = create_tfidf_features(X_train, X_test, max_features=1000)
print(f"TF-IDF特征维度: {X_train_tfidf.shape}")

# 训练朴素贝叶斯
nb_model, nb_metrics = train_naive_bayes(X_train_tfidf, X_test_tfidf, y_train, y_test)
print("\n测试完成！")