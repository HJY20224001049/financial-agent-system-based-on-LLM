@echo off
echo 启动股票分析系统...
cd /d "%~dp0"
echo 当前目录: %CD%
echo 检查Python...
.\streamlit_env\Scripts\python.exe -c "import streamlit; print('Streamlit version:', streamlit.__version__)" 2>nul
if errorlevel 1 (
    echo Streamlit未安装，请先运行 run_app.bat 安装依赖。
    pause
    exit /b 1
)
echo 正在启动Streamlit应用...
echo 如果长时间无响应，请检查浏览器是否打开 http://localhost:8502
echo 按 Ctrl+C 停止应用
.\streamlit_env\Scripts\python.exe -m streamlit run app.py --server.headless false --server.port 8502
pause