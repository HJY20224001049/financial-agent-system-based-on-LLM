# 股票分析系统可视化界面

基于Streamlit构建的用户交互界面，提供用户输入、LLM反馈显示和图表查看功能。

## 功能特点

1. **用户输入界面**：文本输入框，支持多行输入
2. **智能分析**：调用main.py的分析逻辑，支持风险分析、舆情分析、股票预测和数据查询
3. **结果展示**：
   - 显示LLM生成的最终分析报告
   - 展示分析过程中生成的图表（预测图、走势图等）
   - 查看详细的分析过程输出
4. **交互功能**：
   - 开始分析/清除结果按钮
   - 侧边栏使用说明
   - 响应式布局

## 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行应用
```bash
python -m streamlit run app.py
```
或者双击 `run_app.bat`（Windows）

### 环境配置
确保已设置 `DASHSCOPE_API_KEY` 环境变量（用于LLM调用）：
```bash
# Windows
set DASHSCOPE_API_KEY=your_api_key

# Linux/Mac
export DASHSCOPE_API_KEY=your_api_key
```

## 使用说明

1. 启动应用后，在文本框中输入您的问题，例如：
   - "分析贵州茅台的风险"
   - "预测贵州茅台未来股价"
   - "查询贵州茅台的最新数据"
   - "分析贵州茅台的舆情和风险"

2. 点击"开始分析"按钮
3. 等待分析完成（可能需要几分钟）
4. 查看右侧的分析结果：
   - **最终分析报告**：LLM生成的综合性投资建议
   - **分析图表**：预测图表、走势图等
   - **详细输出**：分析过程的详细日志

5. 点击"清除结果"可以重置界面

## 文件说明

- `app.py`：主界面程序
- `requirements.txt`：Python依赖包
- `run_app.bat`：Windows启动脚本
- `run_app.sh`：Linux/Mac启动脚本
- `main.py`：后端分析逻辑（原命令行程序）

## 注意事项

1. 首次使用需要安装依赖（streamlit、matplotlib等）
2. 需要有效的DASHSCOPE_API_KEY才能使用LLM功能
3. 分析过程中会在项目目录生成临时文件（final_analyse.txt、图表文件等）
4. 图表文件命名规则：
   - 预测图表：通常以 `prediction_` 或 `figure_` 开头
   - 其他图表：包含 `stock` 关键词

## 故障排除

### 无法启动应用
- 检查Python版本（需要3.8+）
- 确保已安装依赖：`pip install streamlit matplotlib`
- 如果出现"无法识别streamlit命令"错误，请使用：
  ```bash
  python -m streamlit run app.py
  ```
  或直接运行 `run_app.bat`
- 检查streamlit是否正确安装：`python -m streamlit --version`

### 分析过程中出错
- 检查DASHSCOPE_API_KEY环境变量是否设置
- 查看"详细输出"中的错误信息
- 确保网络连接正常（需要访问股票数据API）
- **protobuf兼容性问题**：如果看到"Descriptors cannot be created directly"错误，运行：
  ```bash
  pip install --upgrade "protobuf<3.20,>=3.9.2"
  ```
  或双击 `fix_protobuf.bat`

### 无法显示图表
- 检查图表文件是否生成
- 确保matplotlib已正确安装
- 查看浏览器控制台是否有错误

## 界面截图

（实际运行后可见）

## 版本历史

- v1.0 (2026-03-23)：初始版本，基于main.py功能实现可视化界面

---

**注意**：本系统基于深度学习模型和传统机器学习模型进行股票预测，分析结果仅供参考，不构成投资建议。