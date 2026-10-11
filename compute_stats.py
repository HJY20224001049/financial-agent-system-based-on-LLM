import pandas as pd
import numpy as np

# 读取数据
df = pd.read_csv('./data/stock_data.csv')
print("数据形状:", df.shape)
print("列名:", df.columns.tolist())

# 提取low和high列
low = df['low'].values
high = df['high'].values

print("\nlow统计:")
print("  均值:", np.mean(low))
print("  标准差:", np.std(low))
print("  最小值:", np.min(low))
print("  最大值:", np.max(low))

print("\nhigh统计:")
print("  均值:", np.mean(high))
print("  标准差:", np.std(high))
print("  最小值:", np.min(high))
print("  最大值:", np.max(high))

# 计算整个数据集的均值和标准差（用于归一化）
# 特征列：open, close, low, high, volume, money, change
feature_cols = ['open', 'close', 'low', 'high', 'volume', 'money', 'change']
for col in feature_cols:
    vals = df[col].values
    print(f"\n{col}: 均值={np.mean(vals):.2f}, 标准差={np.std(vals):.2f}")

# 检查是否有缺失值
print("\n缺失值检查:")
print(df.isnull().sum())

# 检查数据顺序（按日期排序）
if 'date' in df.columns:
    df['date'] = pd.to_datetime(df['date'])
    print("\n日期范围:", df['date'].min(), "到", df['date'].max())
    # 检查是否按日期排序
    is_sorted = (df['date'].diff().dropna() >= pd.Timedelta(0)).all()
    print("是否按日期升序排序:", is_sorted)