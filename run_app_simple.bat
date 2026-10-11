@echo off
echo ========================================
echo 股票分析系统简化启动脚本
echo ========================================
echo 当前目录: %CD%
echo 系统时间: %DATE% %TIME%
echo.

echo 第一步：检查streamlit_env虚拟环境...
if not exist ".\streamlit_env\Scripts\python.exe" (
    echo 错误: streamlit_env虚拟环境不存在！
    echo 请先创建虚拟环境或检查路径。
    pause
    exit /b 1
)
echo 虚拟环境找到。

echo.
echo 第二步：检查streamlit是否安装...
.\streamlit_env\Scripts\python.exe -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Streamlit未安装，正在安装...
    .\streamlit_env\Scripts\python.exe -m pip install -r requirements_streamlit.txt
    if errorlevel 1 (
        echo Streamlit安装失败！
        pause
        exit /b 1
    )
    echo Streamlit安装成功。
) else (
    echo Streamlit已安装。
)

echo.
echo 第三步：启动Streamlit应用...
echo 注意：浏览器将自动打开，请稍候...
echo 如果长时间无响应，请按Ctrl+C终止并检查错误信息。
echo.
.\streamlit_env\Scripts\python.exe -m streamlit run app.py --server.port 8501
echo.
echo Streamlit已退出。
pause