@echo off
cd /d "%~dp0"
echo ========================================
echo 股票分析系统启动脚本 - 调试模式
echo ========================================
echo 当前目录: %CD%
echo 系统时间: %DATE% %TIME%

REM 定义网站URL
set "EASTMONEY_URL=https://www.eastmoney.com/"
set "GUBABA_URL=http://guba.eastmoney.com/"
set "FINNEWS_URL=http://www.financialnews.com.cn/"
set "SINA_STOCK_URL=https://finance.sina.com.cn/stock/"
set "JRJ_URL=https://www.jrj.com.cn/"
set "STCN_URL=http://www.stcn.com/"
set "CFI_URL=http://www.cfi.cn/"

REM 显示导航菜单函数
goto :skip_nav_functions

:show_nav_menu
echo.
echo ========================================
echo             网站导航菜单
echo ========================================
echo  1. 东方财富网 (eastmoney.com)
echo  2. 股吧 (guba.eastmoney.com)
echo  3. 中国金融新闻网 (financialnews.com.cn)
echo  4. 新浪财经股票频道
echo  5. 金融界 (jrj.com.cn)
echo  6. 证券时报网 (stcn.com)
echo  7. 中财网 (cfi.cn)
echo  8. 返回主菜单
echo  9. 退出
echo ========================================
set /p NAV_CHOICE="请选择要访问的网站 (1-9): "

if "%NAV_CHOICE%"=="1" (
    echo 正在打开东方财富网...
    start "" "%EASTMONEY_URL%"
    goto show_nav_menu
)
if "%NAV_CHOICE%"=="2" (
    echo 正在打开股吧...
    start "" "%GUBABA_URL%"
    goto show_nav_menu
)
if "%NAV_CHOICE%"=="3" (
    echo 正在打开中国金融新闻网...
    start "" "%FINNEWS_URL%"
    goto show_nav_menu
)
if "%NAV_CHOICE%"=="4" (
    echo 正在打开新浪财经股票频道...
    start "" "%SINA_STOCK_URL%"
    goto show_nav_menu
)
if "%NAV_CHOICE%"=="5" (
    echo 正在打开金融界...
    start "" "%JRJ_URL%"
    goto show_nav_menu
)
if "%NAV_CHOICE%"=="6" (
    echo 正在打开证券时报网...
    start "" "%STCN_URL%"
    goto show_nav_menu
)
if "%NAV_CHOICE%"=="7" (
    echo 正在打开中财网...
    start "" "%CFI_URL%"
    goto show_nav_menu
)
if "%NAV_CHOICE%"=="8" (
    goto show_main_menu
)
if "%NAV_CHOICE%"=="9" (
    echo 退出网站导航。
    exit /b 0
)
echo 错误: 无效的选择，请重新输入。
goto show_nav_menu

:show_main_menu
echo.
echo ========================================
echo         股票分析系统主菜单
echo ========================================
echo  1. 启动Streamlit分析应用
echo  2. 打开网站导航
echo  3. 股票数据查询模式
echo  4. 显示帮助信息
echo  5. 退出
echo ========================================
set /p MAIN_CHOICE="请选择操作 (1-5): "

if "%MAIN_CHOICE%"=="1" (
    echo 启动Streamlit应用...
    goto skip_help
)
if "%MAIN_CHOICE%"=="2" (
    goto show_nav_menu
)
if "%MAIN_CHOICE%"=="3" (
    echo.
    echo 股票数据查询模式
    echo 用法: run_app.bat query <股票代码> [选项]
    echo.
    set /p QUERY_CODE="请输入股票代码 (如 sh000001): "
    if "%QUERY_CODE%"=="" (
        echo 错误: 股票代码不能为空。
        pause
        goto show_main_menu
    )
    set QUERY_ARGS=%QUERY_CODE%
    set /p QUERY_COUNT="请输入K线数量 [默认10]: "
    if not "%QUERY_COUNT%"=="" (
        set QUERY_ARGS=%QUERY_ARGS% --count %QUERY_COUNT%
    )
    set /p QUERY_FREQ="请输入K线周期 [默认1d]: "
    if not "%QUERY_FREQ%"=="" (
        set QUERY_ARGS=%QUERY_ARGS% --frequency %QUERY_FREQ%
    )
    set /p QUERY_PLOT="是否绘制图表? (y/N): "
    if /i "%QUERY_PLOT%"=="y" (
        set QUERY_ARGS=%QUERY_ARGS% --plot
    )
    echo.
    echo 正在执行查询: query %QUERY_ARGS%
    echo.
    .\streamlit_env\Scripts\python.exe run_query.py query %QUERY_ARGS%
    pause
    goto show_main_menu
)
if "%MAIN_CHOICE%"=="4" (
    goto show_help
)
if "%MAIN_CHOICE%"=="5" (
    echo 退出系统。
    exit /b 0
)
echo 错误: 无效的选择，请重新输入。
goto show_main_menu

:skip_nav_functions
REM 继续执行初始化代码

REM chcp 65001 > nul
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

REM 额外清除所有可能的代理变量，防止Yahoo Finance API连接失败
echo 清除所有代理相关环境变量...
REM 逐个清除代理变量（避免for循环解析问题）
set HTTP_PROXY=
set HTTPS_PROXY=
set http_proxy=
set https_proxy=
set FTP_PROXY=
set ftp_proxy=
set ALL_PROXY=
set all_proxy=
set HTTP_PROXY_USER=
set HTTP_PROXY_PASS=
set HTTPS_PROXY_USER=
set HTTPS_PROXY_PASS=
set npm_config_proxy=
set npm_config_https_proxy=
set npm_config_http_proxy=
set PROXY=
set proxy=
set REQUEST_PROXY=
set request_proxy=
set HTTPS_REQUEST_PROXY=
set https_request_proxy=
set SOCKS_PROXY=
set socks_proxy=
set SOCKS5_PROXY=
set socks5_proxy=
set WINHTTP_PROXY=
set WINHTTP_PROXY_BYPASS=
set WININET_PROXY=
set WININET_PROXY_BYPASS=
set NPM_CONFIG_PROXY=
set NPM_CONFIG_HTTPS_PROXY=
set NPM_CONFIG_HTTP_PROXY=
set YARN_PROXY=
set YARN_HTTPS_PROXY=
set YARN_HTTP_PROXY=
set GLOBAL_AGENT_HTTP_PROXY=
set GLOBAL_AGENT_HTTPS_PROXY=
set GLOBAL_AGENT_FORCE_GLOBAL_AGENT=
set ELECTRON_GET_USE_PROXY=
set NODE_EXTRA_CA_CERTS=
set NPM_CONFIG_CACHE=
set NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=
set NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=
set FORCE_COLOR=
set COLORTERM=
REM 设置NO_PROXY为所有，禁用代理
set NO_PROXY=*
set no_proxy=*
set NODE_NO_HTTP_PROXY=1
set NODE_NO_HTTPS_PROXY=1
REM 设置代理为direct://，强制直接连接
set HTTP_PROXY=direct://
set HTTPS_PROXY=direct://
set http_proxy=direct://
set https_proxy=direct://
REM 设置Python不验证HTTPS（仅用于测试环境）
set PYTHONHTTPSVERIFY=0
REM 设置requests库不使用代理
set REQUESTS_CA_BUNDLE=
set CURL_CA_BUNDLE=


REM 跳过protobuf检查以简化脚本
REM echo 跳过protobuf版本检查...

echo.

:parse_args
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
        REM 查询模式：直接调用Python脚本处理参数
        echo 查询模式：调用Python脚本处理...
        .\streamlit_env\Scripts\python.exe run_query.py %*
        pause
        exit /b 0
    )
    if "%1"=="nav" (
        REM 导航模式：显示网站导航菜单
        goto show_nav_menu
    )
    if "%1"=="menu" (
        REM 菜单模式：显示主菜单
        goto show_main_menu
    )
    echo 错误: 未知命令 %1
    echo.
    goto show_help
)

REM 如果没有参数，显示主菜单
goto show_main_menu

:show_help
echo 用法:
echo   run_app.bat [命令] [选项]
echo.
echo 命令:
echo   query <股票代码>  查询股票数据
echo   nav                打开网站导航菜单
echo   menu               显示交互式主菜单
echo   (无命令)          显示交互式主菜单
echo.
echo 选项 (仅查询模式):
echo   --count <N>        K线数量，默认10
echo   --frequency <F>    K线周期，默认1d，可选: 1d,1w,1M,1m,5m,15m,30m,60m
echo   --end-date <DATE>  结束日期，格式YYYY-MM-DD
echo   --plot             绘制价格折线图
echo   --output <FILE>    图表输出文件路径（默认自动生成）
echo.
echo 示例:
echo   run_app.bat query sh000001 --count 5 --frequency 1d
echo   run_app.bat query 600519 --count 20 --frequency 5m
echo   run_app.bat nav
echo   run_app.bat menu
echo   run_app.bat
echo.
pause
exit /b 0

:skip_help



REM 以下为原始启动Streamlit应用的逻辑
echo.
echo 检查streamlit是否安装...
.\streamlit_env\Scripts\python.exe -c "import streamlit" 2>nul
if errorlevel 1 (
    echo Streamlit未安装，正在安装...
    .\streamlit_env\Scripts\python.exe -m pip install -r requirements_streamlit.txt
)

echo.

REM 检查并安装ashare_mcp模块
echo 检查ashare_mcp模块安装...
.\streamlit_env\Scripts\python.exe -c "import ashare_mcp" 2>nul
if errorlevel 1 (
    echo ashare_mcp未安装，正在安装...
    REM 首先尝试从本地目录安装
    set "LOCAL_ASHARE_PATH=%CD%\Ashare-mcp"
    if exist "%LOCAL_ASHARE_PATH%" (
        echo 从本地目录安装ashare_mcp...
        .\streamlit_env\Scripts\python.exe -m pip install -e "%LOCAL_ASHARE_PATH%"
        if errorlevel 1 (
            echo 本地安装失败，尝试从GitHub安装...
            .\streamlit_env\Scripts\python.exe -m pip install git+https://github.com/RusianHu/Ashare-mcp.git
            if errorlevel 1 (
                echo 警告: ashare_mcp安装失败，历史K线查询功能可能受限。
            ) else (
                echo ashare_mcp从GitHub安装成功。
            )
        ) else (
            echo ashare_mcp本地安装成功。
        )
    ) else (
        echo 本地Ashare-mcp目录不存在，从GitHub安装...
        .\streamlit_env\Scripts\python.exe -m pip install git+https://github.com/RusianHu/Ashare-mcp.git
        if errorlevel 1 (
            echo 警告: ashare_mcp安装失败，历史K线查询功能可能受限。
        ) else (
            echo ashare_mcp从GitHub安装成功。
        )
    )
) else (
    echo ashare_mcp已安装。
)

echo.
REM 禁用MCP股票客户端，避免代理错误导致Yahoo Finance API连接失败
set DISABLE_MCP_STOCK_CLIENT=1
echo 启动Streamlit应用...
REM 使用streamlit虚拟环境中的Python，避免protobuf版本冲突
.\streamlit_env\Scripts\python.exe -m streamlit run app.py --server.headless false --server.port 8502
pause