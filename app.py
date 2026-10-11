import streamlit as st
import subprocess
import os
import sys
import asyncio
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import time
import PyPDF2
import io
import json
from typing import Optional, Dict, Any

# 尝试导入MCP客户端
MCP_AVAILABLE = False
if not os.environ.get('DISABLE_MCP_STOCK_CLIENT'):
    try:
        from mcp_stock_client import MCPStockClient
        MCP_AVAILABLE = True
    except ImportError:
        MCP_AVAILABLE = False
        st.sidebar.warning("MCP客户端未找到，实时查询功能受限。请确保mcp_stock_client.py在项目目录中。")
    except Exception as e:
        MCP_AVAILABLE = False
        st.sidebar.warning(f"MCP客户端导入失败: {e}")
else:
    st.sidebar.info("MCP股票客户端已通过环境变量禁用，实时报价功能不可用。")

# 尝试导入Ashare MCP客户端
try:
    from ashare_mcp_client import AshareMCPClient
    ASHARE_MCP_AVAILABLE = True
except ImportError:
    ASHARE_MCP_AVAILABLE = False
    st.sidebar.warning("Ashare MCP客户端未找到，历史数据查询功能受限。请确保ashare_mcp_client.py在项目目录中。")
except Exception as e:
    ASHARE_MCP_AVAILABLE = False
    st.sidebar.warning(f"Ashare MCP客户端导入失败: {e}")

# 尝试直接导入ashare_mcp模块，用于历史K线查询
ASHARE_DIRECT_AVAILABLE = False
ASHARE_DIRECT_WARNING = ""
try:
    # 添加本地Ashare-mcp目录到sys.path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    ashare_mcp_dir = os.path.join(current_dir, "Ashare-mcp")
    ashare_mcp_dir = os.path.abspath(ashare_mcp_dir)
    if ashare_mcp_dir not in sys.path:
        sys.path.insert(0, ashare_mcp_dir)

    from ashare_mcp.server import get_price
    ASHARE_DIRECT_AVAILABLE = True
except ImportError as e:
    ASHARE_DIRECT_AVAILABLE = False
    ASHARE_DIRECT_WARNING = f"直接导入ashare_mcp模块失败: {e}"
except Exception as e:
    ASHARE_DIRECT_AVAILABLE = False
    ASHARE_DIRECT_WARNING = f"导入ashare_mcp模块时出错: {e}"

# 配置：main.py 使用的 Python 解释器路径
# main.py 需要 TensorFlow + PyTorch，而界面所在的虚拟环境（streamlit_env）
# 可能没装它们，所以按以下优先级自动选择解释器：
#   1. 环境变量 STOCK_MAIN_PYTHON 显式指定
#   2. 当前解释器（若它已装好 tensorflow —— 单环境部署时就是这种情况）
#   3. 开发机上并存的系统 Python（双环境部署时使用）
#   4. 兜底：当前解释器
def _pick_main_python():
    override = os.environ.get("STOCK_MAIN_PYTHON")
    if override and os.path.isfile(override):
        return override
    try:
        import importlib.util
        if importlib.util.find_spec("tensorflow") is not None:
            return sys.executable
    except Exception:
        pass
    for candidate in (r"E:\python3.9\python.exe",):
        if os.path.isfile(candidate):
            return candidate
    return sys.executable


MAIN_PYTHON_PATH = _pick_main_python()
# 如需强制指定，可设环境变量 STOCK_MAIN_PYTHON，例如：r"venv\Scripts\python.exe"

# 异步获取股票数据函数
async def get_stock_price_async(code: str, count: int = 10, frequency: str = '1d', end_date: str = ''):
    """异步获取股票价格数据"""
    try:
        if not ASHARE_DIRECT_AVAILABLE:
            return None, "ashare_mcp模块不可用，无法获取历史数据"

        result = await get_price(
            code=code,
            end_date=end_date,
            count=count,
            frequency=frequency
        )
        return result, None
    except Exception as e:
        return None, f"获取股票数据时出错: {str(e)}"

# 同步包装函数，用于在Streamlit中调用
def get_stock_price(code: str, count: int = 10, frequency: str = '1d', end_date: str = ''):
    """同步获取股票价格数据（内部处理异步调用）"""
    try:
        return asyncio.run(get_stock_price_async(code, count, frequency, end_date))
    except RuntimeError as e:
        # 如果已有事件循环（如在Jupyter或某些环境中），尝试使用nest_asyncio
        if "cannot be called from a running event loop" in str(e):
            try:
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.run(get_stock_price_async(code, count, frequency, end_date))
            except ImportError:
                return None, "需要nest_asyncio来处理现有事件循环"
        return None, f"运行异步函数时出错: {str(e)}"
    except Exception as e:
        return None, f"获取股票数据时出错: {str(e)}"

# PDF文本提取函数
def extract_pdf_text(pdf_path):
    """提取PDF文件的文本内容"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        return text.strip()
    except Exception as e:
        return f"提取PDF文本失败: {str(e)}"

# 分析函数
def run_analysis_locally(question):
    """在项目根目录运行分析"""
    original_dir = os.getcwd()

    # 确保我们在项目根目录
    project_root = Path(original_dir)

    # 准备输出文件列表（运行前记录已有文件）
    existing_files = set(project_root.glob("*.txt")) | set(project_root.glob("*.csv")) | set(project_root.glob("*.png")) | set(project_root.glob("*.jpg"))

    stdout = ""
    stderr = ""
    return_code = None

    try:
        # 运行main.py - 将stderr重定向到stdout避免IndexError问题
        process = subprocess.Popen(
            [MAIN_PYTHON_PATH, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 重定向stderr到stdout
            text=True,
            encoding='gbk',
            errors='replace',
            cwd=project_root
        )

        try:
            result = process.communicate(input=question + "\n", timeout=300)
            stdout = result[0] if result and len(result) > 0 else ""
            stderr = ""  # stderr已重定向到stdout
            return_code = process.returncode
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                result = process.communicate()
                stdout = result[0] if result and len(result) > 0 else ""
            except Exception as kill_error:
                stdout = f"进程终止时出错: {str(kill_error)}"
            stderr = ""
            return_code = process.returncode
            return {'error': '分析超时', 'stdout': stdout, 'return_code': return_code}
        except Exception as e:
            # 捕获其他可能的通信错误
            return {'error': f'子进程通信错误: {str(e)}', 'stdout': stdout if 'stdout' in locals() else ""}

    except Exception as e:
        # 捕获Popen或其他错误
        return {'error': f'启动分析进程失败: {str(e)}'}

    # 检查进程是否正常退出
    if return_code != 0:
        return {'error': f'分析进程异常退出，返回码: {return_code}', 'stdout': stdout}

    # 获取新生成的文件
    new_files = set(project_root.glob("*.txt")) | set(project_root.glob("*.csv")) | set(project_root.glob("*.png")) | set(project_root.glob("*.jpg"))
    generated_files = new_files - existing_files

    # 读取final_analyse.txt（可能已存在）
    final_report = ""
    try:
        if (project_root / "final_analyse.txt").exists():
            final_report = (project_root / "final_analyse.txt").read_text(encoding='utf-8')
    except Exception as e:
        final_report = f"读取分析报告失败: {str(e)}"

    # 收集图表文件
    chart_files = []
    image_files = []
    pdf_files = []

    # 1. 收集根目录的图像文件（原有逻辑）
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        for img_file in project_root.glob(ext):
            # 排除可能无关的图表
            if img_file.name.startswith('prediction') or img_file.name.startswith('figure') or 'stock' in img_file.name.lower():
                chart_files.append(str(img_file))
                image_files.append(str(img_file))

    # 2. 收集figure文件夹中的图像文件
    figure_dir = project_root / "figure"
    if figure_dir.exists():
        for ext in ['*.png', '*.jpg', '*.jpeg']:
            for img_file in figure_dir.glob(ext):
                image_files.append(str(img_file))

    # 3. 收集results文件夹中的PDF文件
    results_dir = project_root / "results"
    if results_dir.exists():
        for pdf_file in results_dir.glob("*.pdf"):
            pdf_files.append(str(pdf_file))

    return {
        'stdout': stdout,
        'stderr': stderr,
        'final_report': final_report,
        'chart_files': chart_files,  # 向后兼容
        'image_files': image_files,
        'pdf_files': pdf_files,
        'generated_files': [str(f) for f in generated_files],
        'return_code': return_code
    }

# 设置页面
st.set_page_config(page_title="股票分析系统", layout="wide")
st.title("📈 股票分析系统")
st.markdown("输入您的问题，系统将进行风险分析、舆情分析、股票预测等综合评估。")

# 快速网站导航
st.markdown("### 🌐 快速访问")
nav_cols = st.columns(7)
with nav_cols[0]:
    st.link_button("东方财富网", "https://www.eastmoney.com/", use_container_width=True)
with nav_cols[1]:
    st.link_button("股吧", "http://guba.eastmoney.com/", use_container_width=True)
with nav_cols[2]:
    st.link_button("金融新闻网", "http://www.financialnews.com.cn/", use_container_width=True)
with nav_cols[3]:
    st.link_button("新浪财经", "https://finance.sina.com.cn/stock/", use_container_width=True)
with nav_cols[4]:
    st.link_button("金融界", "https://www.jrj.com.cn/", use_container_width=True)
with nav_cols[5]:
    st.link_button("证券时报", "http://www.stcn.com/", use_container_width=True)
with nav_cols[6]:
    st.link_button("中财网", "http://www.cfi.cn/", use_container_width=True)

st.markdown("---")

# 创建标签页
tab1, tab2 = st.tabs(["综合分析", "实时查询"])

# 初始化session state
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False
if 'final_report' not in st.session_state:
    st.session_state.final_report = ""
if 'chart_files' not in st.session_state:
    st.session_state.chart_files = []
if 'output_text' not in st.session_state:
    st.session_state.output_text = ""
if 'image_files' not in st.session_state:
    st.session_state.image_files = []
if 'pdf_files' not in st.session_state:
    st.session_state.pdf_files = []
# MCP实时查询相关状态
if 'realtime_symbol' not in st.session_state:
    st.session_state.realtime_symbol = ""
if 'realtime_data' not in st.session_state:
    st.session_state.realtime_data = None
if 'realtime_error' not in st.session_state:
    st.session_state.realtime_error = ""
if 'realtime_client' not in st.session_state:
    st.session_state.realtime_client = None
# Ashare MCP查询相关状态
if 'ashare_data_source' not in st.session_state:
    st.session_state.ashare_data_source = "realtime"  # realtime 或 historical
if 'ashare_frequency' not in st.session_state:
    st.session_state.ashare_frequency = "1d"
if 'ashare_count' not in st.session_state:
    st.session_state.ashare_count = 10
if 'ashare_end_date' not in st.session_state:
    st.session_state.ashare_end_date = ""
if 'ashare_historical_data' not in st.session_state:
    st.session_state.ashare_historical_data = None
if 'ashare_client' not in st.session_state:
    st.session_state.ashare_client = None

with tab2:
    st.header("📊 实时股票查询")
    st.markdown("使用MCP股票分析服务器获取实时股票数据，或使用Ashare MCP获取历史K线数据。")

    # 股票代码输入
    symbol_input = st.text_input(
        "股票代码",
        placeholder="例如：AAPL (美股), 600519.SS (A股上证), 000001.SZ (A股深证)",
        key="realtime_symbol_input"
    )

    # 数据源选择
    col_ds1, col_ds2, col_ds3 = st.columns([1, 1, 2])
    with col_ds1:
        data_source = st.radio(
            "数据源",
            options=["实时报价", "历史K线"],
            index=0 if st.session_state.ashare_data_source == "realtime" else 1,
            key="data_source_select",
            horizontal=True
        )
    with col_ds2:
        if data_source == "历史K线":
            frequency = st.selectbox(
                "K线周期",
                options=["1d", "1w", "1M", "1m", "5m", "15m", "30m", "60m"],
                index=0,
                key="frequency_select"
            )
            st.session_state.ashare_frequency = frequency
    with col_ds3:
        if data_source == "历史K线":
            count = st.number_input("K线数量", min_value=1, max_value=1000, value=10, key="count_input")
            st.session_state.ashare_count = count

    col_a, col_b, col_c = st.columns([1, 1, 6])
    with col_a:
        query_btn = st.button("查询股票数据", type="primary", use_container_width=True, key="query_realtime_btn")
    with col_b:
        clear_realtime_btn = st.button("清除结果", use_container_width=True, key="clear_realtime_btn")

    if clear_realtime_btn:
        st.session_state.realtime_data = None
        st.session_state.realtime_error = ""
        st.rerun()

    # 查询股票数据
    if query_btn and symbol_input.strip():
        symbol = symbol_input.strip().upper()

        if data_source == "实时报价":
            st.session_state.realtime_symbol = symbol
            st.session_state.realtime_data = None
            st.session_state.realtime_error = ""
            st.session_state.ashare_historical_data = None

            with st.spinner(f"正在获取 {symbol} 的实时数据..."):
                try:
                    # 检查MCP可用性
                    if not MCP_AVAILABLE:
                        st.error("MCP客户端不可用，请确保mcp_stock_client.py在项目目录中。")
                    else:
                        # 初始化客户端（如果尚未初始化）
                        if st.session_state.realtime_client is None:
                            env = {}
                            # 可选的NEWS_API_KEY
                            if "NEWS_API_KEY" in os.environ:
                                env["NEWS_API_KEY"] = os.environ["NEWS_API_KEY"]
                            st.session_state.realtime_client = MCPStockClient(env=env)

                        client = st.session_state.realtime_client

                        # 启动服务器（如果未运行）
                        if not client.running:
                            if not client.start():
                                st.error("无法启动MCP服务器。请确保Node.js和npm已安装，并且可以运行: npx mcp-stock-analysis-server")
                            else:
                                time.sleep(2)  # 等待服务器初始化

                        # 获取实时报价
                        quote = client.get_stock_quote(symbol, use_fallback=True)

                        if quote and not quote.get('isError'):
                            # 额外检查content是否包含错误消息
                            has_error = False
                            if 'content' in quote and isinstance(quote['content'], list):
                                for item in quote['content']:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        text = item.get('text', '')
                                        if any(keyword in text.lower() for keyword in ['error', '错误', '失败', 'not found', '无法']):
                                            has_error = True
                                            break
                            if has_error:
                                # 提取错误消息
                                error_msg = ''
                                for item in quote['content']:
                                    if isinstance(item, dict) and item.get('type') == 'text':
                                        error_msg = item.get('text', '未知错误')
                                        break
                                st.session_state.realtime_error = f"获取数据失败: {error_msg}"
                            else:
                                st.session_state.realtime_data = quote
                                st.success(f"成功获取 {symbol} 实时数据")
                        else:
                            if quote and quote.get('isError'):
                                # 提取错误消息
                                error_msg = '未知错误'
                                if 'content' in quote and isinstance(quote['content'], list):
                                    for item in quote['content']:
                                        if isinstance(item, dict) and item.get('type') == 'text':
                                            error_msg = item.get('text', '未知错误')
                                            break
                                st.session_state.realtime_error = f"MCP错误: {error_msg}"
                            else:
                                st.session_state.realtime_error = f"无法获取 {symbol} 的实时数据。请检查股票代码是否正确，或稍后重试。"
                except Exception as e:
                    st.session_state.realtime_error = f"查询过程中出错: {str(e)}"
                    import traceback
                    st.error(f"错误详情: {traceback.format_exc()}")
        else:  # 历史K线
            st.session_state.realtime_data = None
            st.session_state.realtime_error = ""
            st.session_state.ashare_historical_data = None

            with st.spinner(f"正在获取 {symbol} 的历史K线数据（{st.session_state.ashare_frequency}）..."):
                try:
                    # 检查ashare_mcp直接导入可用性
                    if not ASHARE_DIRECT_AVAILABLE:
                        st.error(f"ashare_mcp模块不可用，无法获取历史数据。{ASHARE_DIRECT_WARNING}")
                    else:
                        # 获取历史数据
                        frequency = st.session_state.ashare_frequency
                        count = st.session_state.ashare_count
                        end_date = st.session_state.ashare_end_date

                        # 转换股票代码格式：如果输入的是普通A股代码，转换为sh/sz前缀
                        # 假设A股代码：6开头上海，0开头深圳
                        converted_symbol = symbol
                        if symbol.isdigit():
                            if symbol.startswith(('60', '68')):
                                converted_symbol = f"sh{symbol}"
                            elif symbol.startswith(('00', '30')):
                                converted_symbol = f"sz{symbol}"

                        # 直接调用ashare_mcp获取数据
                        data, error = get_stock_price(converted_symbol, count=count, frequency=frequency, end_date=end_date)

                        if error:
                            st.session_state.realtime_error = f"获取数据失败: {error}"
                        elif data:
                            # 将Result对象转换为字典格式，与原有代码兼容
                            if hasattr(data, 'data'):
                                result_dict = {
                                    'code': data.code,
                                    'data': data.data,
                                    'message': data.message
                                }
                                st.session_state.ashare_historical_data = result_dict
                                st.success(f"成功获取 {symbol} 历史数据（{frequency}，{count}条）")
                            else:
                                st.session_state.ashare_historical_data = data
                                st.success(f"成功获取 {symbol} 历史数据（{frequency}，{count}条）")
                        else:
                            st.session_state.realtime_error = f"无法获取 {symbol} 的历史数据。请检查股票代码是否正确，或稍后重试。"
                except Exception as e:
                    st.session_state.realtime_error = f"查询过程中出错: {str(e)}"
                    import traceback
                    st.error(f"错误详情: {traceback.format_exc()}")

    # 显示实时数据结果
    if st.session_state.realtime_error:
        st.error(st.session_state.realtime_error)

    if st.session_state.realtime_data:
        quote = st.session_state.realtime_data
        st.subheader(f"{quote.get('symbol', st.session_state.realtime_symbol)} 实时行情")

        # 创建两列布局显示关键数据
        col1, col2 = st.columns(2)

        with col1:
            st.metric("当前价格",
                     f"{quote.get('price', 'N/A')}",
                     delta=f"{quote.get('change', 'N/A')} ({quote.get('changePercent', 'N/A')}%)")

            st.write("**基本数据**")
            st.write(f"- 开盘价: {quote.get('open', 'N/A')}")
            st.write(f"- 最高价: {quote.get('high', 'N/A')}")
            st.write(f"- 最低价: {quote.get('low', 'N/A')}")

        with col2:
            st.write("**交易数据**")
            st.write(f"- 成交量: {quote.get('volume', 'N/A')}")
            st.write(f"- 成交额: {quote.get('amount', 'N/A')}")
            st.write(f"- 更新时间: {quote.get('timestamp', 'N/A')}")

        # 显示原始JSON数据（可选）
        with st.expander("查看原始数据"):
            st.json(quote)

    # 显示历史K线数据结果
    if st.session_state.ashare_historical_data:
        data = st.session_state.ashare_historical_data
        st.subheader(f"{data.get('code', symbol_input)} 历史K线（{st.session_state.ashare_frequency}）")

        # 解析数据
        if data.get('data') and 'records' in data['data']:
            records = data['data']['records']
            if records:
                # 创建DataFrame用于显示
                import pandas as pd
                df = pd.DataFrame(records)
                # 重命名列
                column_map = {
                    'time': '时间',
                    'day': '日期',
                    'open': '开盘价',
                    'high': '最高价',
                    'low': '最低价',
                    'close': '收盘价',
                    'volume': '成交量'
                }
                df.rename(columns={k: v for k, v in column_map.items() if k in df.columns}, inplace=True)

                # 显示数据表
                st.dataframe(df, use_container_width=True)

                # 绘制K线图（简单折线图）
                try:
                    import plotly.graph_objects as go
                    from plotly.subplots import make_subplots

                    # 寻找时间列（支持中英文列名）
                    date_col = None
                    possible_date_cols = ['时间', '日期', 'time', 'day', 'date', 'datetime']
                    for col in possible_date_cols:
                        if col in df.columns:
                            date_col = col
                            break

                    # 如果找到了时间列，尝试转换为datetime类型
                    if date_col:
                        try:
                            # 如果列是字符串类型，尝试转换为datetime
                            if df[date_col].dtype == 'object':
                                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                        except Exception:
                            pass  # 转换失败，保持原样

                    # 查找价格列（支持中英文列名）
                    price_col = None
                    possible_price_cols = ['收盘价', 'close', '收盘', 'price', 'last']
                    for col in possible_price_cols:
                        if col in df.columns:
                            price_col = col
                            break

                    # 查找成交量列（支持中英文列名）
                    volume_col = None
                    possible_volume_cols = ['成交量', 'volume', '成交量', 'vol', 'amount']
                    for col in possible_volume_cols:
                        if col in df.columns:
                            volume_col = col
                            break

                    # 确保至少找到价格列
                    if price_col:
                        # 根据是否有时间列选择X轴数据
                        if date_col and date_col in df.columns:
                            x_data = df[date_col]
                            x_label = '时间'
                        else:
                            x_data = list(range(len(df)))
                            x_label = '数据索引'
                            st.warning("未找到标准时间列，使用数据索引作为X轴绘制图表。")

                        # 创建图表
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                           vertical_spacing=0.03, subplot_titles=('价格走势', '成交量'),
                                           row_heights=[0.7, 0.3])

                        # 添加价格线
                        fig.add_trace(go.Scatter(x=x_data, y=df[price_col],
                                                mode='lines', name='价格',
                                                line=dict(color='blue', width=2)),
                                     row=1, col=1)

                        # 添加成交量柱状图（如果找到成交量列）
                        if volume_col and volume_col in df.columns:
                            fig.add_trace(go.Bar(x=x_data, y=df[volume_col],
                                                name='成交量', marker_color='orange'),
                                         row=2, col=1)

                        # 更新布局
                        fig.update_layout(height=600, showlegend=True,
                                         xaxis_rangeslider_visible=False,
                                         xaxis_title=x_label)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error("未找到价格数据列，无法绘制图表。")
                except ImportError:
                    st.warning("未安装plotly，无法绘制交互式图表。请安装: pip install plotly")
                except Exception as e:
                    st.error(f"绘制图表时出错: {e}")

        # 显示原始JSON数据（可选）
        with st.expander("查看原始数据"):
            st.json(data)

    # 显示使用说明
    with st.expander("使用说明"):
        st.markdown("""
        **支持的股票代码格式：**
        - 美股: AAPL, GOOGL, MSFT
        - A股上证: 600519.SS 或 sh600519
        - A股深证: 000001.SZ 或 sz000001
        - 港股: 0700.HK
        - 指数: ^GSPC (标普500), ^IXIC (纳斯达克)

        **数据源：**
        - **实时报价**: MCP股票分析服务器（需要Node.js环境）
        - **历史K线**: Ashare MCP服务器（基于新浪/腾讯财经，需要Python环境）
        - **备用**: 东方财富API（仅A股实时数据）

        **注意事项：**
        - 首次查询可能需要几秒钟启动MCP服务器
        - 实时报价需要Node.js和npm环境
        - 历史K线需要ashare_mcp模块（pip install ashare_mcp）
        - 新闻情感分析需要设置NEWS_API_KEY环境变量
        """)

    # 检查Node.js环境
    with st.expander("环境检查"):
        try:
            import subprocess
            result = subprocess.run("node --version", shell=True, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                st.success(f"✅ Node.js 已安装: {result.stdout.strip()}")
            else:
                st.warning("⚠️ Node.js 未安装或不可用。MCP服务器可能无法启动。")
        except Exception as e:
            st.warning(f"⚠️ 检查Node.js时出错: {e}")

    # 检查Python和ashare_mcp环境
    with st.expander("Python环境检查"):
        try:
            import subprocess
            # 检查Python版本
            python_result = subprocess.run("python --version", shell=True, capture_output=True, text=True, check=False)
            if python_result.returncode == 0:
                st.success(f"✅ Python 已安装: {python_result.stdout.strip()}")
            else:
                st.warning("⚠️ Python 未安装或不可用。")

            # 尝试导入ashare_mcp
            try:
                import ashare_mcp
                st.success("✅ ashare_mcp 模块已安装")
            except ImportError:
                st.warning("⚠️ ashare_mcp 模块未安装。历史K线功能可能无法使用。")
                st.info("安装方法: pip install git+https://github.com/RusianHu/Ashare-mcp.git")
        except Exception as e:
            st.warning(f"⚠️ 检查Python环境时出错: {e}")

    # 股票数据源网站导航
    st.markdown("---")
    st.subheader("📊 股票数据源网站")
    st.markdown("以下网站提供股票行情、新闻和分析数据：")

    data_cols = st.columns(4)
    with data_cols[0]:
        st.link_button("东方财富数据", "https://data.eastmoney.com/", use_container_width=True)
    with data_cols[1]:
        st.link_button("新浪财经数据", "https://finance.sina.com.cn/stock/", use_container_width=True)
    with data_cols[2]:
        st.link_button("腾讯财经", "https://finance.qq.com/", use_container_width=True)
    with data_cols[3]:
        st.link_button("同花顺数据", "http://www.10jqka.com.cn/", use_container_width=True)

    st.markdown("💡 **提示**: 这些网站提供实时行情、历史数据、财务报表等股票相关信息。")

with tab1:
    # 用户输入
    user_input = st.text_area("请输入您的问题（例如：分析贵州茅台的风险和预测未来股价）:",
                              height=100,
                              placeholder="例如：分析贵州茅台的风险和预测未来股价",
                              key="user_input_area")

    col1, col2, col3 = st.columns([1, 1, 6])
    with col1:
        analyze_btn = st.button("开始分析", type="primary", use_container_width=True, key="analyze_btn")
    with col2:
        clear_btn = st.button("清除结果", use_container_width=True, key="clear_results_btn")

    if clear_btn:
        st.session_state.analysis_done = False
        st.session_state.final_report = ""
        st.session_state.chart_files = []
        st.session_state.image_files = []
        st.session_state.pdf_files = []
        st.session_state.output_text = ""
        st.rerun()
    # 执行分析
    if analyze_btn and user_input.strip():
        st.write("分析按钮已点击，开始分析...")  # 调试信息
        with st.spinner("正在分析中，这可能需要几分钟..."):
            analysis_result = run_analysis_locally(user_input.strip())

            if 'error' in analysis_result:
                error_msg = analysis_result['error']
                if 'stdout' in analysis_result and analysis_result['stdout']:
                    stdout_preview = analysis_result['stdout'][:500]
                    error_msg += f"\n\n输出内容:\n{stdout_preview}..."

                    # 检查是否是protobuf/TensorFlow兼容性问题
                    if "Descriptors cannot be created directly" in analysis_result['stdout'] or "protobuf" in analysis_result['stdout'].lower():
                        error_msg += "\n\n检测到protobuf版本兼容性问题！"
                        error_msg += "\nTensorFlow需要protobuf < 3.20，但当前版本太高。"
                        error_msg += "\n请运行 fix_protobuf.bat 或执行: pip install --upgrade 'protobuf<3.20,>=3.9.2'"

                st.error(f"分析过程中出错: {error_msg}")
            else:
                st.session_state.analysis_done = True
                st.session_state.final_report = analysis_result.get('final_report', '')
                st.session_state.chart_files = analysis_result.get('chart_files', [])
                st.session_state.image_files = analysis_result.get('image_files', [])
                st.session_state.pdf_files = analysis_result.get('pdf_files', [])
                st.session_state.output_text = analysis_result.get('stdout', '')

                # 显示成功信息
                st.success("分析完成！")

    # 显示结果
    if st.session_state.analysis_done:
        # 显示最终分析结果
        if st.session_state.final_report:
            st.subheader("📊 最终分析报告")
            with st.expander("查看完整报告", expanded=True):
                st.text_area("报告内容", st.session_state.final_report, height=300, key="final_report_area")

        # 显示图像图表
        if st.session_state.image_files:
            st.subheader("📈 分析图表")
            # 按两列布局
            cols = st.columns(2)
            for i, chart_path in enumerate(st.session_state.image_files):
                col_idx = i % 2
                with cols[col_idx]:
                    try:
                        img = mpimg.imread(chart_path)
                        st.image(img, caption=Path(chart_path).name, use_column_width=True)
                    except Exception as e:
                        st.error(f"无法加载图表 {chart_path}: {e}")

        # 显示PDF报告
        if st.session_state.pdf_files:
            st.subheader("📄 风险分析报告")
            for pdf_path in st.session_state.pdf_files:
                with st.expander(f"📋 {Path(pdf_path).name}"):
                    try:
                        pdf_text = extract_pdf_text(pdf_path)
                        st.text_area("报告内容", pdf_text, height=200, key=f"pdf_{Path(pdf_path).name}")
                    except Exception as e:
                        st.error(f"读取PDF文件失败 {pdf_path}: {e}")

        # 如果都没有生成图表或报告
        if not st.session_state.image_files and not st.session_state.pdf_files:
            st.info("本次分析未生成图表或报告。")

        # 显示原始输出（调试用）
        with st.expander("查看详细输出"):
            if st.session_state.output_text:
                st.text("分析过程输出:")
                st.code(st.session_state.output_text)
            else:
                st.text("无输出内容")

# 侧边栏信息
with st.sidebar:
    st.header("ℹ️ 使用说明")
    st.markdown("""
    1. 在文本框中输入您的问题
    2. 点击"开始分析"按钮
    3. 系统将自动进行：
       - 意图识别
       - 股票数据查询
       - 风险分析
       - 舆情分析
       - 股票预测
       - 生成综合报告
    4. 查看右侧的分析结果和图表

    **支持的分析类型：**
    - 风险分析（意图1）
    - 舆情分析（意图2）
    - 股票预测（意图3）
    - 查询数字数据（意图4）
    """)

    if st.session_state.analysis_done:
        st.header("📁 生成文件")
        if st.session_state.image_files:
            st.text("图像文件:")
            for img_file in st.session_state.image_files:
                st.text(f"  • {Path(img_file).name}")
        if st.session_state.pdf_files:
            st.text("PDF报告:")
            for pdf_file in st.session_state.pdf_files:
                st.text(f"  • {Path(pdf_file).name}")

    st.divider()

    # 网站导航
    st.header("🌐 网站导航")
    st.markdown("点击以下链接快速访问常用财经网站：")

    with st.expander("📊 财经资讯网站"):
        st.markdown("""
        - [东方财富网](https://www.eastmoney.com/) - 综合财经资讯、行情数据
        - [股吧](http://guba.eastmoney.com/) - 投资者交流平台
        - [中国金融新闻网](http://www.financialnews.com.cn/) - 权威金融新闻
        - [新浪财经股票频道](https://finance.sina.com.cn/stock/) - 股票行情与分析
        - [金融界](https://www.jrj.com.cn/) - 专业财经媒体
        - [证券时报网](http://www.stcn.com/) - 证券权威媒体
        - [中财网](http://www.cfi.cn/) - 财经信息门户
        """)

    with st.expander("📈 数据查询工具"):
        st.markdown("""
        - [新浪财经](https://finance.sina.com.cn/) - 行情数据查询
        - [腾讯财经](https://finance.qq.com/) - 财经新闻与数据
        - [东方财富数据中心](https://data.eastmoney.com/) - 深度数据统计
        - [同花顺](http://www.10jqka.com.cn/) - 行情软件与数据分析
        """)

    st.markdown("💡 **提示**: 点击链接将在新标签页中打开网站")

    st.divider()
    st.caption("股票分析系统 v1.0")

# 页脚
st.divider()
st.caption("注：本系统基于深度学习模型和传统机器学习模型进行股票预测，分析结果仅供参考，不构成投资建议。")