#!/bin/bash
echo "正在启动股票分析系统..."
echo "请确保已设置DASHSCOPE_API_KEY环境变量"
echo "如果未安装依赖，请运行：pip install -r requirements.txt"
echo ""

# 检查streamlit是否安装
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Streamlit未安装，正在安装..."
    pip install streamlit matplotlib
fi

echo "启动Streamlit应用..."
# 使用python -m streamlit，避免PATH问题
python -m streamlit run app.py