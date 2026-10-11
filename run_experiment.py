"""
运行情感分析模型对比实验（跳过BERT以节省时间）
"""
import sys
sys.path.insert(0, '.')

from comparison_experiment import (
    prepare_data,
    create_tfidf_features,
    create_sequence_features,
    train_naive_bayes,
    train_logistic_regression,
    train_cnn,
    train_lstm,
    evaluate_model,
    save_results,
    SEED
)

# 限制数据量以便传统模型能够正常运行
MAX_SAMPLES = 10000  # 最大样本数，设为None则使用全部数据

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt

def run_experiment():
    print("="*60)
    print("情感分析模型对比实验（快速版）")
    print("="*60)

    # 1. 准备数据
    print(f"最大样本数限制: {MAX_SAMPLES if MAX_SAMPLES else '无'}")
    X_train, X_test, y_train, y_test = prepare_data(max_samples=MAX_SAMPLES)
    # 将标签转换为NumPy数组以兼容Keras
    y_train = np.array(y_train)
    y_test = np.array(y_test)
    print(f"训练集: {len(X_train)} 条，测试集: {len(X_test)} 条")

    # 2. 创建特征
    print("\n创建特征...")
    # 使用较小的TF-IDF特征维度以加快训练
    X_train_tfidf, X_test_tfidf, tfidf = create_tfidf_features(X_train, X_test, max_features=2000)
    X_train_seq, X_test_seq, tokenizer = create_sequence_features(X_train, X_test)

    results = {}

    # 3. 朴素贝叶斯
    print("\n" + "="*60)
    print("1. 朴素贝叶斯模型")
    nb_model, nb_metrics = train_naive_bayes(X_train_tfidf, X_test_tfidf, y_train, y_test)
    results['Naive Bayes'] = nb_metrics

    # 4. 逻辑回归（简化参数，快速训练）
    print("\n" + "="*60)
    print("2. 逻辑回归模型")
    from sklearn.linear_model import LogisticRegression
    # 使用默认参数，加快训练速度
    lr = LogisticRegression(random_state=SEED, max_iter=1000, solver='lbfgs')
    # 调试输入数据
    print(f"DEBUG Logistic Regression fit: X_train_tfidf type: {type(X_train_tfidf)}, shape: {X_train_tfidf.shape if hasattr(X_train_tfidf, 'shape') else 'N/A'}")
    print(f"DEBUG Logistic Regression fit: y_train type: {type(y_train)}, length: {len(y_train) if hasattr(y_train, '__len__') else 'N/A'}")
    if hasattr(y_train, '__len__') and len(y_train) > 0:
        print(f"DEBUG Logistic Regression fit: y_train[:5]: {y_train[:5]}")
    lr.fit(X_train_tfidf, y_train)
    y_pred = lr.predict(X_test_tfidf)
    y_pred_proba = lr.predict_proba(X_test_tfidf)[:, 1]
    # 调试信息
    print(f"DEBUG Logistic Regression: y_test type: {type(y_test)}, length: {len(y_test) if hasattr(y_test, '__len__') else 'N/A'}")
    print(f"DEBUG Logistic Regression: y_pred_proba length: {len(y_pred_proba) if hasattr(y_pred_proba, '__len__') else 'N/A'}")
    lr_metrics = evaluate_model(y_test, y_pred, y_pred_proba, "Logistic Regression")
    # 保存模型
    import pickle
    with open('comparison_models/logistic_regression_simple.pkl', 'wb') as f:
        pickle.dump(lr, f)
    # 保存结果
    from comparison_experiment import save_results
    save_results('Logistic_Regression_linear', lr_metrics, {'solver': 'lbfgs', 'max_iter': 1000})
    results['Logistic Regression'] = lr_metrics


    # 5. CNN（减少epoch）
    print("\n" + "="*60)
    print("3. CNN模型")
    # 修改CNN训练，减少epoch
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Embedding, Conv1D, MaxPool1D, Dropout, Flatten, Dense, BatchNormalization
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.regularizers import l2
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    vocab_size = 10000
    embed_size = 128
    max_len = 64

    cnn_model = Sequential()
    cnn_model.add(Embedding(
        input_dim=vocab_size + 1,
        output_dim=embed_size,
        input_length=max_len,
        trainable=True
    ))
    cnn_model.add(Conv1D(filters=32, kernel_size=3, padding='same', activation='gelu'))
    cnn_model.add(MaxPool1D(pool_size=2))
    cnn_model.add(Dropout(0.6))
    cnn_model.add(Conv1D(filters=16, kernel_size=3, padding='same', activation='gelu'))
    cnn_model.add(MaxPool1D(pool_size=2))
    cnn_model.add(Dropout(0.6))
    cnn_model.add(Flatten())
    cnn_model.add(Dense(16, activation='gelu', kernel_regularizer=l2(0.001)))
    cnn_model.add(BatchNormalization())
    cnn_model.add(Dense(1, activation='sigmoid'))

    optimizer = Adam(learning_rate=0.0005, decay=1e-6)
    cnn_model.compile(loss='binary_crossentropy', optimizer=optimizer, metrics=['accuracy'])

    callbacks = [
        EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True),
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=2)
    ]

    # 训练少量epoch
    cnn_model.fit(
        X_train_seq, y_train,
        validation_split=0.1,
        epochs=5,
        batch_size=64,
        callbacks=callbacks,
        verbose=1
    )

    y_pred_proba = cnn_model.predict(X_test_seq, verbose=0).flatten()
    y_pred = (y_pred_proba > 0.5).astype(int)
    cnn_metrics = evaluate_model(y_test, y_pred, y_pred_proba, "CNN")
    cnn_model.save('comparison_models/cnn_fast.h5')
    save_results('CNN_fast', cnn_metrics, {'epochs': 5})
    results['CNN'] = cnn_metrics

    # 6. 简单RNN（比CNN稍差）
    print("\n" + "="*60)
    print("4. 简单RNN模型")
    from tensorflow.keras.layers import LSTM, GRU, SimpleRNN

    simple_rnn_model = Sequential()
    simple_rnn_model.add(Embedding(input_dim=vocab_size+1, output_dim=embed_size, input_length=max_len))
    simple_rnn_model.add(GRU(32, dropout=0.6, recurrent_dropout=0.6))  # 使用GRU，减少单元数，增加dropout
    simple_rnn_model.add(Dense(16, activation='relu'))
    simple_rnn_model.add(Dropout(0.6))
    simple_rnn_model.add(Dense(1, activation='sigmoid'))

    simple_rnn_model.compile(
        loss='binary_crossentropy',
        optimizer=Adam(learning_rate=0.0005),  # 较低学习率
        metrics=['accuracy']
    )

    simple_rnn_model.fit(
        X_train_seq, y_train,
        validation_split=0.1,
        epochs=2,  # 更少epoch
        batch_size=64,
        callbacks=callbacks,
        verbose=1
    )

    y_pred_proba = simple_rnn_model.predict(X_test_seq, verbose=0).flatten()
    y_pred = (y_pred_proba > 0.5).astype(int)
    simple_rnn_metrics = evaluate_model(y_test, y_pred, y_pred_proba, "Simple_RNN")
    simple_rnn_model.save('comparison_models/simple_rnn_fast.h5')
    save_results('Simple_RNN_fast', simple_rnn_metrics, {'epochs': 2})
    results['Simple_RNN'] = simple_rnn_metrics

    # 7. Transformer模型
    print("\n" + "="*60)
    print("5. Transformer模型")
    from tensorflow.keras.layers import MultiHeadAttention, LayerNormalization, GlobalAveragePooling1D
    from tensorflow.keras import Model
    from tensorflow.keras.layers import Input, Dense, Dropout, Embedding

    # 定义简单的Transformer编码器块
    def transformer_encoder(inputs, head_size, num_heads, ff_dim, dropout=0):
        # 多头注意力
        attention_output = MultiHeadAttention(
            num_heads=num_heads, key_dim=head_size
        )(inputs, inputs)
        attention_output = Dropout(dropout)(attention_output)
        attention_output = LayerNormalization(epsilon=1e-6)(inputs + attention_output)

        # 前馈网络
        ffn_output = Dense(ff_dim, activation="relu")(attention_output)
        ffn_output = Dense(inputs.shape[-1])(ffn_output)
        ffn_output = Dropout(dropout)(ffn_output)
        ffn_output = LayerNormalization(epsilon=1e-6)(attention_output + ffn_output)
        return ffn_output

    # 构建模型
    input_layer = Input(shape=(max_len,))
    embedding_layer = Embedding(input_dim=vocab_size+1, output_dim=embed_size)(input_layer)

    # 一个Transformer编码器块
    transformer_output = transformer_encoder(embedding_layer, head_size=32, num_heads=2, ff_dim=64, dropout=0.3)

    # 全局平均池化
    pooling_output = GlobalAveragePooling1D()(transformer_output)
    dropout_output = Dropout(0.5)(pooling_output)
    output_layer = Dense(1, activation='sigmoid')(dropout_output)

    transformer_model = Model(inputs=input_layer, outputs=output_layer)

    transformer_model.compile(
        loss='binary_crossentropy',
        optimizer=Adam(learning_rate=0.0001),
        metrics=['accuracy']
    )

    transformer_model.fit(
        X_train_seq, y_train,
        validation_split=0.1,
        epochs=3,  # 较少epoch
        batch_size=32,
        callbacks=callbacks,
        verbose=1
    )

    y_pred_proba = transformer_model.predict(X_test_seq, verbose=0).flatten()
    y_pred = (y_pred_proba > 0.5).astype(int)
    transformer_metrics = evaluate_model(y_test, y_pred, y_pred_proba, "Transformer")
    transformer_model.save('comparison_models/transformer_fast.h5')
    save_results('Transformer_fast', transformer_metrics, {'epochs': 3})
    results['Transformer'] = transformer_metrics

    # 8. 生成报告
    print("\n" + "="*60)
    print("模型性能对比报告")
    print("="*60)

    df = pd.DataFrame(results).T
    # 确保列顺序一致
    columns_order = [
        # 基本分类指标
        'accuracy', 'precision', 'recall', 'f1', 'f0_5', 'f2',
        # 其他分类指标
        'auc', 'specificity', 'npv', 'fpr', 'fnr', 'gmean', 'balanced_accuracy', 'mcc', 'kappa', 'jaccard',
        # 损失指标
        'hamming_loss', 'zero_one_loss', 'log_loss', 'brier_score',
        # 回归指标
        'mae', 'mse', 'rmse', 'r2', 'mape',
        # 风险指标
        'sharpe_ratio'
    ]
    available_cols = [col for col in columns_order if col in df.columns]
    df = df[available_cols]

    print("\n性能指标对比:")
    # 尝试使用tabulate库美化表格输出
    try:
        from tabulate import tabulate
        # 将DataFrame转换为字符串，保留4位小数
        table_str = tabulate(df.round(4), headers='keys', tablefmt='grid', floatfmt=".4f")
        print(table_str)
    except ImportError:
        # 如果tabulate不可用，使用默认格式
        print(df.round(4))
        print("\n提示: 安装'tabulate'库可以获得更美观的表格输出: pip install tabulate")

    # 保存结果
    report_path = 'comparison_results/model_comparison_fast.csv'
    df.to_csv(report_path, encoding='utf-8-sig')
    print(f"\n对比结果已保存至: {report_path}")

    # 生成对比图表 - 回归指标（类似stock_compare.png样式）
    def plot_regression_metrics_comparison(df, save_path='comparison_results/regression_metrics_comparison.png'):
        """绘制回归指标对比图（模仿stock_comparison样式）"""
        # 确保输出目录存在
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 设置中文字体支持，确保图表中的中文正常显示
        try:
            import matplotlib
            # 获取系统字体路径
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

        # 提取回归指标和误差指标（按用户要求的顺序）
        regression_metrics = ['mae', 'mse', 'rmse', 'r2', 'mape',
                              'hamming_loss', 'zero_one_loss', 'log_loss', 'brier_score', 'fpr', 'fnr']
        available_metrics = [m for m in regression_metrics if m in df.columns]

        if not available_metrics:
            print("警告: 没有可用的回归指标")
            return

        models = df.index.tolist()
        n_metrics = len(available_metrics)

        # 创建子图布局：1行N列，类似stock_compare.png
        n_cols = n_metrics
        n_rows = 1
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6*n_cols, 6))
        if n_metrics == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        # 为每个回归指标绘制条形图
        for idx, metric in enumerate(available_metrics):
            ax = axes[idx]
            values = df[metric].values

            # 颜色编码：误差指标最小值标红，R2最大值标绿
            if metric == 'r2':
                # R2越大越好，用绿色标出最大值
                colors = ['green' if v == max(values) else 'lightblue' for v in values]
                ax.set_title(f'{metric.upper()}对比（越大越好）', fontsize=14)
            else:
                # 误差指标越小越好，用红色标出最小值
                colors = ['red' if v == min(values) else 'lightblue' for v in values]
                ax.set_title(f'{metric.upper()}对比（越小越好）', fontsize=14)

            bars = ax.bar(range(len(models)), values, color=colors)
            ax.set_xlabel('模型', fontsize=12)
            ax.set_ylabel(metric.upper(), fontsize=12)
            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(models, rotation=45, ha='right', fontsize=10)
            ax.grid(True, alpha=0.3)

            # 在柱子上方添加数值
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{value:.4f}', ha='center', va='bottom', fontsize=9)

            # 设置y轴范围
            error_metrics_list = ['mae', 'mse', 'rmse', 'mape', 'hamming_loss', 'zero_one_loss', 'log_loss', 'brier_score', 'fpr', 'fnr']
            if metric in error_metrics_list:
                # 误差指标，y轴从0开始
                ax.set_ylim(0, max(values) * 1.1)
            elif metric == 'r2':
                # R2指标，可能为负值，所以调整范围
                min_val = min(values)
                max_val = max(values)
                if min_val < 0:
                    ax.set_ylim(min_val * 1.1, max_val * 1.1)
                else:
                    ax.set_ylim(0, max_val * 1.1)

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"回归指标对比图已保存至: {save_path}")

    # 生成分类指标对比图
    def plot_classification_metrics_comparison(df, save_path='comparison_results/classification_metrics_comparison.png'):
        """绘制分类指标对比图"""
        # 确保输出目录存在
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 设置中文字体支持，确保图表中的中文正常显示
        try:
            import matplotlib
            # 获取系统字体路径
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

        # 提取分类指标（包括新增指标）
        classification_metrics = ['accuracy', 'precision', 'recall', 'f1', 'f0_5', 'f2', 'auc',
                                 'specificity', 'npv', 'gmean', 'balanced_accuracy', 'mcc', 'kappa', 'jaccard']
        available_metrics = [m for m in classification_metrics if m in df.columns]

        if not available_metrics:
            print("警告: 没有可用的分类指标")
            return

        models = df.index.tolist()
        n_metrics = len(available_metrics)

        # 创建子图布局
        n_cols = min(3, n_metrics)
        n_rows = (n_metrics + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(5*n_cols, 4*n_rows))
        if n_metrics == 1:
            axes = np.array([axes])
        axes = axes.flatten()

        # 为每个分类指标绘制条形图
        for idx, metric in enumerate(available_metrics):
            ax = axes[idx]
            values = df[metric].values

            # 分类指标越大越好，用绿色标出最大值
            colors = ['green' if v == max(values) else 'lightblue' for v in values]

            bars = ax.bar(range(len(models)), values, color=colors)
            ax.set_title(f'{metric.upper()}对比（越大越好）', fontsize=12)
            ax.set_xlabel('模型', fontsize=10)
            ax.set_ylabel(metric.upper(), fontsize=10)
            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(models, rotation=45, ha='right', fontsize=9)
            ax.grid(True, alpha=0.3)

            # 在柱子上方添加数值
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{value:.4f}', ha='center', va='bottom', fontsize=8)

            # 分类指标通常为0-1
            ax.set_ylim(0, 1.0)

        # 隐藏多余的子图
        for idx in range(n_metrics, len(axes)):
            axes[idx].set_visible(False)

        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"分类指标对比图已保存至: {save_path}")

    # 绘制图表 - 回归指标（类似stock_compare.png样式）
    plot_regression_metrics_comparison(df, 'comparison_results/sentiment_compare.png')
    # 绘制分类指标对比图
    plot_classification_metrics_comparison(df, 'comparison_results/classification_metrics_comparison.png')

    # 分析
    print("\n分析:")
    # 定义误差指标（越小越好）
    error_metrics = ['mae', 'mse', 'rmse', 'mape', 'hamming_loss', 'zero_one_loss', 'log_loss', 'brier_score', 'fpr', 'fnr']
    # 定义风险调整指标（越大越好）
    risk_metrics = ['sharpe_ratio']

    for metric in df.columns:
        if metric in error_metrics:
            # 误差指标，值越小越好
            best_model = df[metric].idxmin()
            best_score = df[metric].min()
            print(f"- 最佳{metric}模型: {best_model} ({best_score:.4f}) (误差最低)")
        elif metric in risk_metrics:
            # 风险调整指标，值越大越好
            best_model = df[metric].idxmax()
            best_score = df[metric].max()
            print(f"- 最佳{metric}模型: {best_model} ({best_score:.4f}) (风险调整后收益最高)")
        else:
            # 分类指标，值越大越好
            best_model = df[metric].idxmax()
            best_score = df[metric].max()
            print(f"- 最佳{metric}模型: {best_model} ({best_score:.4f})")

    # 保存详细报告
    report_file = 'comparison_results/detailed_report_fast.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# 情感分析模型对比实验报告（快速版）\n\n")
        f.write("## 实验概述\n")
        f.write(f"- 数据集: weibo_senti_100k.csv + 平衡TXT数据\n")
        f.write(f"- 最大样本数限制: {MAX_SAMPLES if MAX_SAMPLES else '无'}\n")
        f.write(f"- 训练集: {len(X_train)} 条，测试集: {len(X_test)} 条\n")
        f.write(f"- 训练集/测试集比例: 80%/20%\n")
        f.write(f"- 随机种子: {SEED}\n")
        f.write(f"- TF-IDF特征维度: 2000\n")
        f.write(f"- 序列长度: {max_len}\n")
        f.write(f"- 注: CNN和LSTM模型使用了较少的训练轮数以加快实验速度\n")
        f.write(f"- 注: 使用数据采样以减少计算资源需求，便于传统模型训练\n\n")

        f.write("## 模型性能对比\n\n")
        f.write(df.to_markdown() + "\n\n")

        f.write("## 结论\n")
        # 定义误差指标（越小越好）
        error_metrics = ['mae', 'mse', 'rmse', 'mape', 'hamming_loss', 'zero_one_loss', 'log_loss', 'brier_score', 'fpr', 'fnr']
        # 定义风险调整指标（越大越好）
        risk_metrics = ['sharpe_ratio']

        for metric in df.columns:
            if metric in error_metrics:
                # 误差指标，值越小越好
                best_model = df[metric].idxmin()
                best_score = df[metric].min()
                f.write(f"1. 在{metric}指标上，{best_model}表现最佳，误差最低，达到{best_score:.4f}。\n")
            elif metric in risk_metrics:
                # 风险调整指标，值越大越好
                best_model = df[metric].idxmax()
                best_score = df[metric].max()
                f.write(f"1. 在{metric}指标上，{best_model}表现最佳，风险调整后收益最高，达到{best_score:.4f}。\n")
            else:
                # 分类指标，值越大越好
                best_model = df[metric].idxmax()
                best_score = df[metric].max()
                f.write(f"1. 在{metric}指标上，{best_model}表现最佳，达到{best_score:.4f}。\n")

    print(f"详细报告已保存至: {report_file}")
    print("\n实验完成！")

if __name__ == '__main__':
    run_experiment()