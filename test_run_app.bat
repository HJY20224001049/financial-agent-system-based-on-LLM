@echo off
echo 正在启动股票分析系统...
echo 请确保已设置DASHSCOPE_API_KEY环境变量
echo.

REM 清除代理环境变量，解决MCP服务器连接问题
echo 清除代理环境变量...
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set NO_PROXY=*
set no_proxy=*
set NODE_NO_HTTP_PROXY=1
set NODE_NO_HTTPS_PROXY=1
set NODE_TLS_REJECT_UNAUTHORIZED=0

REM 检查protobuf版本兼容性
echo 检查protobuf版本兼容性...
python -c "
try:
    import google.protobuf
    version = google.protobuf.__version__
    major_version = int(version.split('.')[0])
    if major_version >= 4:
        print(f'警告: protobuf版本 {version} 可能与TensorFlow不兼容')
        print('TensorFlow需要protobuf < 3.20')
        print('建议运行 fix_protobuf.bat 修复')
    else:
        print(f'protobuf版本: {version} (正常)')
except ImportError:
    print('未安装protobuf')
" 2>nul

echo.

REM 解析命令行参数
set MODE=app
set STOCK_CODE=
set COUNT=10
set FREQUENCY=1d
set END_DATE=

REM 显示帮助信息
if "%1"=="--help" goto show_help
if "%1"=="-h" goto show_help

if not "%1"=="" (
    if "%1"=="query" (
        set MODE=query
        shift
        set STOCK_CODE=%1
        if "%STOCK_CODE%"=="" (
            echo 错误: 查询模式需要指定股票代码。
            echo.
            goto show_help
        )
        shift

        :parse_args
        if "%1"=="" goto args_done
        if "%1"=="--count" (
            shift
            set COUNT=%1
            shift
            goto parse_args
        )
        if "%1"=="--frequency" (
            shift
            set FREQUENCY=%1
            shift
            goto parse_args
        )
        if "%1"=="--end-date" (
            shift
            set END_DATE=%1
            shift
            goto parse_args
        )
        REM 未知参数
        echo 警告: 忽略未知参数 %1
        shift
        goto parse_args
        :args_done
    ) else (
        echo 错误: 未知命令 %1
        echo.
        goto show_help
    )
)

goto skip_help

:show_help
echo 用法:
echo   run_app.bat [命令] [选项]
echo.
echo 命令:
echo   query <股票代码>  查询股票数据
echo   (无命令)          启动Streamlit应用
echo.
echo 选项 (仅查询模式):
echo   --count <N>        K线数量，默认10
echo   --frequency <F>    K线周期，默认1d，可选: 1d,1w,1M,1m,5m,15m,30m,60m
echo   --end-date <DATE>  结束日期，格式YYYY-MM-DD
echo.
echo 示例:
echo   run_app.bat query sh000001 --count 5 --frequency 1d
echo   run_app.bat query 600519 --count 20 --frequency 5m
echo   run_app.bat
echo.
pause
exit /b 0

:skip_help

echo 检查ashare_mcp模块是否安装...
python -c "import ashare_mcp" 2>nul
if errorlevel 1 (
    echo ashare_mcp未安装，正在安装...
    echo 从GitHub安装ashare_mcp模块...
    python -m pip install git+https://github.com/RusianHu/Ashare-mcp.git
    if errorlevel 1 (
        echo 安装ashare_mcp失败，查询功能可能不可用。
    ) else (
        echo ashare_mcp安装成功。
    )
) else (
    echo ashare_mcp已安装。
)

if "%MODE%"=="query" (
    echo 执行股票数据查询...
    echo 股票代码: %STOCK_CODE%
    echo 数量: %COUNT%
    echo 频率: %FREQUENCY%
    if not "%END_DATE%"=="" echo 结束日期: %END_DATE%
    echo.

    REM 调用ashare_mcp_client.py进行查询
    echo 正在查询数据，请稍候...
    python query_stock.py %STOCK_CODE% --count %COUNT% --frequency %FREQUENCY% --end-date %END_DATE%
    rem pause
    exit /b 0
)

REM 以下为原始启动Streamlit应用的逻辑
echo.
echo 检查streamlit是否安装...
.\streamlit_env\Scripts\python.exe -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Streamlit未安装，正在安装...
    .\streamlit_env\Scripts\python.exe -m pip install -r requirements_streamlit.txt
)

echo.
echo 启动Streamlit应用...
REM 使用streamlit虚拟环境中的Python，避免protobuf版本冲突
.\streamlit_env\Scripts\python.exe -m streamlit run app.py
pause