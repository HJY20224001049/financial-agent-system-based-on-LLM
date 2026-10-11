@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
echo 正在启动 MCP 股票分析快速开始...
echo.

REM 检查Python是否可用
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误: Python未找到，请确保Python已安装并添加到PATH
    echo 或者使用完整路径: E:\python3.9\python.exe quick_start_mcp.py
    pause
    exit /b 1
)

echo 使用Python版本:
python --version
echo.

python quick_start_mcp.py

echo.
echo 完成! 按任意键退出...
pause > nul