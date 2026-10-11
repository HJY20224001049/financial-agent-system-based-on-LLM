# -*- coding: UTF-8 -*-
"""
股票预测模型定义
包括：LSTM、SVM、Transformer、随机森林、XGBoost
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset
from sklearn.svm import SVR
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from xgboost import XGBRegressor
import pickle
import os


class LSTMModel(nn.Module):
    """LSTM模型（与原模型一致）"""

    def __init__(self, config):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(
            input_size=config.input_size,
            hidden_size=config.hidden_size,
            num_layers=config.lstm_layers,
            batch_first=True,
            dropout=config.dropout_rate if config.lstm_layers > 1 else 0
        )
        self.linear = nn.Linear(config.hidden_size, config.output_size)

    def forward(self, x, hidden=None):
        lstm_out, hidden = self.lstm(x, hidden)
        linear_out = self.linear(lstm_out)
        return linear_out, hidden


class TransformerModel(nn.Module):
    """Transformer时间序列预测模型"""

    def __init__(self, config):
        super(TransformerModel, self).__init__()
        self.config = config

        # 输入嵌入层
        self.input_embedding = nn.Linear(config.input_size, config.transformer_d_model)

        # 位置编码
        self.pos_encoder = PositionalEncoding(config.transformer_d_model, config.time_step)

        # Transformer编码器
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.transformer_d_model,
            nhead=config.transformer_nhead,
            dim_feedforward=config.transformer_dim_feedforward,
            dropout=config.transformer_dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.transformer_num_layers
        )

        # 输出层
        self.decoder = nn.Sequential(
            nn.Linear(config.transformer_d_model, 64),
            nn.ReLU(),
            nn.Dropout(config.transformer_dropout),
            nn.Linear(64, config.output_size)
        )

    def forward(self, x):
        # x形状: [batch_size, time_step, input_size]
        x = self.input_embedding(x)  # [batch_size, time_step, d_model]
        x = self.pos_encoder(x)
        x = self.transformer_encoder(x)
        # 取最后一个时间步的输出
        x = x[:, -1, :]  # [batch_size, d_model]
        x = self.decoder(x)  # [batch_size, output_size]
        return x


class PositionalEncoding(nn.Module):
    """位置编码"""

    def __init__(self, d_model, max_len=5000):
        super(PositionalEncoding, self).__init__()

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # [1, max_len, d_model]

        self.register_buffer('pe', pe)

    def forward(self, x):
        # x形状: [batch_size, seq_len, d_model]
        x = x + self.pe[:, :x.size(1), :]
        return x


class SVMModel:
    """SVM回归模型（使用scikit-learn）"""

    def __init__(self, config):
        self.config = config
        # 使用MultiOutputRegressor包装SVR，支持多输出回归
        self.model = MultiOutputRegressor(
            SVR(
                kernel=config.svm_kernel,
                C=config.svm_C,
                gamma=config.svm_gamma
            ),
            n_jobs=-1
        )

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """训练模型"""
        print("训练SVM模型...")
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X):
        """预测"""
        return self.model.predict(X)

    def save(self, path):
        """保存模型"""
        with open(path, 'wb') as f:
            pickle.dump(self.model, f)

    def load(self, path):
        """加载模型"""
        with open(path, 'rb') as f:
            self.model = pickle.load(f)


class RandomForestModel:
    """随机森林回归模型"""

    def __init__(self, config):
        self.config = config
        self.model = RandomForestRegressor(
            n_estimators=config.rf_n_estimators,
            max_depth=config.rf_max_depth,
            random_state=config.random_seed,
            n_jobs=-1
        )

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """训练模型"""
        print("训练随机森林模型...")
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X):
        """预测"""
        return self.model.predict(X)

    def save(self, path):
        """保存模型"""
        with open(path, 'wb') as f:
            pickle.dump(self.model, f)

    def load(self, path):
        """加载模型"""
        with open(path, 'rb') as f:
            self.model = pickle.load(f)


class XGBoostModel:
    """XGBoost回归模型"""

    def __init__(self, config):
        self.config = config
        self.model = XGBRegressor(
            n_estimators=config.xgb_n_estimators,
            max_depth=config.xgb_max_depth,
            learning_rate=config.xgb_learning_rate,
            random_state=config.random_seed,
            n_jobs=-1
        )

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """训练模型"""
        print("训练XGBoost模型...")
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X):
        """预测"""
        return self.model.predict(X)

    def save(self, path):
        """保存模型"""
        self.model.save_model(path)

    def load(self, path):
        """加载模型"""
        self.model.load_model(path)


class DecisionTreeModel:
    """决策树回归模型"""

    def __init__(self, config):
        self.config = config
        self.model = DecisionTreeRegressor(
            max_depth=config.dt_max_depth,
            random_state=config.random_seed
        )

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """训练模型"""
        print("训练决策树模型...")
        self.model.fit(X_train, y_train)
        return self

    def predict(self, X):
        """预测"""
        return self.model.predict(X)

    def save(self, path):
        """保存模型"""
        import pickle
        with open(path, 'wb') as f:
            pickle.dump(self.model, f)

    def load(self, path):
        """加载模型"""
        import pickle
        with open(path, 'rb') as f:
            self.model = pickle.load(f)


def train_lstm(config, train_data, val_data, logger):
    """训练LSTM模型"""
    train_x, train_y = train_data
    val_x, val_y = val_data

    # 转换为Tensor
    train_x = torch.from_numpy(train_x).float()
    train_y = torch.from_numpy(train_y).float()
    val_x = torch.from_numpy(val_x).float()
    val_y = torch.from_numpy(val_y).float()

    # 创建DataLoader
    train_dataset = TensorDataset(train_x, train_y)
    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)

    val_dataset = TensorDataset(val_x, val_y)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size)

    # 设备设置
    device = torch.device("cuda:0" if config.use_cuda and torch.cuda.is_available() else "cpu")

    # 初始化模型
    model = LSTMModel(config).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = nn.MSELoss()

    # 训练循环
    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(config.epoch):
        model.train()
        train_losses = []

        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)

            optimizer.zero_grad()
            outputs, _ = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            train_losses.append(loss.item())

        # 验证
        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs, _ = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_losses.append(loss.item())

        avg_train_loss = np.mean(train_losses)
        avg_val_loss = np.mean(val_losses)

        logger.info(f"Epoch {epoch+1}/{config.epoch}: "
                   f"Train Loss: {avg_train_loss:.6f}, Val Loss: {avg_val_loss:.6f}")

        # 早停
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            # 保存最佳模型
            torch.save(model.state_dict(), os.path.join(config.model_save_path, "lstm_best.pth"))
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                logger.info(f"早停于第 {epoch+1} 轮")
                break

    # 加载最佳模型
    model.load_state_dict(torch.load(os.path.join(config.model_save_path, "lstm_best.pth")))
    return model


def train_transformer(config, train_data, val_data, logger):
    """训练Transformer模型"""
    train_x, train_y = train_data
    val_x, val_y = val_data

    # 转换为Tensor
    train_x = torch.from_numpy(train_x).float()
    train_y = torch.from_numpy(train_y).float()
    val_x = torch.from_numpy(val_x).float()
    val_y = torch.from_numpy(val_y).float()

    # 对于Transformer，我们需要调整标签形状
    # 原标签形状: [batch_size, time_step, output_size]
    # Transformer输出形状: [batch_size, output_size] (只预测最后一个时间步)
    # 所以我们取每个样本的最后一个时间步作为目标
    train_y = train_y[:, -1, :]  # [batch_size, output_size]
    val_y = val_y[:, -1, :]

    # 创建DataLoader
    train_dataset = TensorDataset(train_x, train_y)
    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True)

    val_dataset = TensorDataset(val_x, val_y)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size)

    # 设备设置
    device = torch.device("cuda:0" if config.use_cuda and torch.cuda.is_available() else "cpu")

    # 初始化模型
    model = TransformerModel(config).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = nn.MSELoss()

    # 训练循环
    best_val_loss = float('inf')
    patience_counter = 0

    for epoch in range(config.epoch):
        model.train()
        train_losses = []

        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)

            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()

            train_losses.append(loss.item())

        # 验证
        model.eval()
        val_losses = []
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_losses.append(loss.item())

        avg_train_loss = np.mean(train_losses)
        avg_val_loss = np.mean(val_losses)

        logger.info(f"Epoch {epoch+1}/{config.epoch}: "
                   f"Train Loss: {avg_train_loss:.6f}, Val Loss: {avg_val_loss:.6f}")

        # 早停
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            patience_counter = 0
            torch.save(model.state_dict(), os.path.join(config.model_save_path, "transformer_best.pth"))
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                logger.info(f"早停于第 {epoch+1} 轮")
                break

    # 加载最佳模型
    model.load_state_dict(torch.load(os.path.join(config.model_save_path, "transformer_best.pth")))
    return model