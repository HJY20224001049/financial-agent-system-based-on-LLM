"""
MCP Stock Analysis Client
用于与 mcp-stock-analysis-server 交互的Python客户端
快速开始: 需要安装Node.js和npm, 然后运行 npx mcp-stock-analysis-server
配置参考: https://www.scnet.cn/ui/aihub/mcp/renchang1016/stock-mcp
"""

import subprocess
import json
import time
import threading
import queue
import sys
import os
import platform
import shutil
from typing import Optional, Dict, Any, List, Union

class MCPStockClient:
    """MCP股票分析客户端

    通过子进程与 mcp-stock-analysis-server 通信
    使用MCP协议(JSON-RPC over stdio)
    """

    def __init__(self, server_command: List[str] = None, env: Dict[str, str] = None):
        """
        初始化MCP客户端

        Args:
            server_command: 启动MCP服务器的命令，默认使用 npx mcp-stock-analysis-server
            env: 环境变量，如 NEWS_API_KEY
        """
        if server_command is None:
            # 根据平台确定npx命令
            is_windows = platform.system() == "Windows"
            npx_cmd = "npx.cmd" if is_windows else "npx"
            # 尝试查找完整路径
            npx_path = shutil.which(npx_cmd)
            if npx_path:
                self.server_command = [npx_path, "-y", "mcp-stock-analysis-server"]
            else:
                self.server_command = [npx_cmd, "-y", "mcp-stock-analysis-server"]
        else:
            self.server_command = server_command

        self.env = env or {}
        self.process = None
        self.request_queue = queue.Queue()
        self.response_map = {}
        self.next_id = 1
        self.read_thread = None
        self.write_thread = None
        self.running = False
        self.initialized = False  # 是否已完成MCP协议初始化

    def _send_request(self, method: str, params: Dict = None, timeout: int = 30) -> Optional[Dict]:
        """发送JSON-RPC请求并等待响应

        Args:
            method: 方法名
            params: 参数
            timeout: 超时时间（秒）

        Returns:
            响应结果或None
        """
        if not self.running or not self.process:
            raise RuntimeError("MCP服务器未运行")

        request_id = self.next_id
        self.next_id += 1

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        if params is not None:
            request["params"] = params

        response_queue = queue.Queue()
        self.response_map[request_id] = response_queue
        self.request_queue.put(request)

        try:
            response = response_queue.get(timeout=timeout)

            if 'error' in response:
                print(f"JSON-RPC请求错误 (方法: {method}): {response['error']}")
                return None

            return response.get('result', {})

        except queue.Empty:
            print(f"等待响应超时 (方法: {method})")
            return None
        finally:
            self.response_map.pop(request_id, None)

    def _initialize(self) -> bool:
        """执行MCP协议初始化握手

        Returns:
            初始化是否成功
        """
        try:
            print("执行MCP协议初始化...")

            # 1. 发送initialize请求
            init_params = {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp_stock_client",
                    "version": "1.0.0"
                }
            }

            init_result = self._send_request("initialize", init_params, timeout=10)
            if init_result is None:
                print("MCP初始化失败: 未收到initialize响应")
                return False

            print(f"MCP初始化成功, 服务器信息: {init_result.get('serverInfo', {})}")

            # 2. 发送initialized通知
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            }
            self.request_queue.put(initialized_notification)

            self.initialized = True
            return True

        except Exception as e:
            print(f"MCP初始化过程中出错: {e}")
            return False

    def start(self):
        """启动MCP服务器子进程"""
        try:
            # 合并环境变量
            env = os.environ.copy()
            env.update(self.env)

            # 打印原始代理设置用于调试
            print("[代理调试] 原始代理相关环境变量:")
            for key, value in env.items():
                if 'proxy' in key.lower():
                    print(f"  {key} = {value}")

            # 清除所有可能的代理设置，避免连接失败
            proxy_keys = [
                # 标准代理环境变量
                'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
                'FTP_PROXY', 'ftp_proxy', 'ALL_PROXY', 'all_proxy',
                # Windows可能使用的代理设置
                'HTTP_PROXY_USER', 'HTTP_PROXY_PASS', 'HTTPS_PROXY_USER', 'HTTPS_PROXY_PASS',
                # Node.js/NPM特定代理
                'npm_config_proxy', 'npm_config_https_proxy', 'npm_config_http_proxy',
                # 其他可能的代理设置
                'PROXY', 'proxy', 'NODE_TLS_REJECT_UNAUTHORIZED',
                # 更多常见代理变量
                'REQUEST_PROXY', 'request_proxy', 'HTTPS_REQUEST_PROXY', 'https_request_proxy',
                'SOCKS_PROXY', 'socks_proxy', 'SOCKS5_PROXY', 'socks5_proxy'
            ]
            for key in proxy_keys:
                if key in env:
                    print(f"[INFO] 移除代理环境变量 {key}")
                    del env[key]
            # 设置NO_PROXY为所有，禁用所有代理
            env['NO_PROXY'] = '*'
            env['no_proxy'] = '*'
            # 明确禁用Node.js的代理
            env['NODE_NO_HTTP_PROXY'] = '1'
            env['NODE_NO_HTTPS_PROXY'] = '1'
            env['NODE_DISABLE_COLOR'] = '1'  # 禁用颜色输出，避免编码问题

            # 额外清除：查找所有包含proxy的变量并删除
            proxy_keys_to_remove = []
            for key in env.keys():
                if 'proxy' in key.lower():
                    proxy_keys_to_remove.append(key)
            for key in proxy_keys_to_remove:
                if key not in ['NO_PROXY', 'no_proxy', 'NODE_NO_HTTP_PROXY', 'NODE_NO_HTTPS_PROXY']:
                    print(f"[INFO] 额外移除代理变量: {key}")
                    del env[key]

            # 设置代理变量为direct://，强制直接连接，避免使用系统代理
            env['HTTP_PROXY'] = 'direct://'
            env['HTTPS_PROXY'] = 'direct://'
            env['http_proxy'] = 'direct://'
            env['https_proxy'] = 'direct://'
            # Node.js相关
            env['ELECTRON_GET_USE_PROXY'] = '0'
            env['GLOBAL_AGENT_HTTP_PROXY'] = ''
            env['GLOBAL_AGENT_HTTPS_PROXY'] = ''
            env['GLOBAL_AGENT_FORCE_GLOBAL_AGENT'] = 'false'
            # 更多Node.js代理禁用
            env['NODE_EXTRA_CA_CERTS'] = ''
            env['NPM_CONFIG_PROXY'] = ''
            env['NPM_CONFIG_HTTPS_PROXY'] = ''
            env['NPM_CONFIG_HTTP_PROXY'] = ''
            env['NPM_CONFIG_NOPROXY'] = '*'
            env['YARN_PROXY'] = ''
            env['YARN_HTTPS_PROXY'] = ''
            env['YARN_HTTP_PROXY'] = ''
            # 禁用Node.js的TLS拒绝（注意安全风险）
            env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
            # Node.js选项：禁用代理并设置其他选项
            node_options = '--max-http-header-size=16384'
            # 如果已有NODE_OPTIONS，合并
            if 'NODE_OPTIONS' in env:
                node_options = env['NODE_OPTIONS'] + ' ' + node_options
            env['NODE_OPTIONS'] = node_options

            # 尝试通过设置全局代理变量为空来禁用代理
            env['GLOBAL_AGENT_ENVIRONMENT_VARIABLE_NAMESPACE'] = ''  # 禁用global-agent
            env['GLOBAL_TUNNEL_AGENT_ENVIRONMENT_VARIABLE_NAMESPACE'] = ''  # 禁用global-tunnel-agent
            env['GLOBAL_AGENT_NO_PROXY'] = '*'

            # 设置Windows特定的代理禁用
            env['WINHTTP_PROXY'] = ''
            env['WINHTTP_PROXY_BYPASS'] = '<local>'
            env['WININET_PROXY'] = ''
            env['WININET_PROXY_BYPASS'] = '<local>'

            # 更多Node.js代理禁用
            env['NPM_CONFIG_PROXY_CACHE'] = ''
            env['NPM_CONFIG_FETCH_RETRY_MINTIMEOUT'] = '10000'
            env['NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT'] = '60000'
            env['FORCE_COLOR'] = '0'
            env['COLORTERM'] = 'nocolor'

            # 设置代理为直接连接（如果需要代理功能但禁用）
            env['GLOBAL_AGENT_HTTP_PROXY'] = 'direct://'
            env['GLOBAL_AGENT_HTTPS_PROXY'] = 'direct://'

            # 设置npm缓存目录到用户目录，避免权限问题
            if 'npm_config_cache' not in env:
                user_cache_dir = os.path.join(os.path.expanduser('~'), '.npm-cache')
                os.makedirs(user_cache_dir, exist_ok=True)
                env['npm_config_cache'] = user_cache_dir
                print(f"[INFO] 设置npm缓存目录: {user_cache_dir}")

            # 打印清理后的代理设置
            print("[代理调试] 清理后的代理相关环境变量:")
            for key, value in env.items():
                if 'proxy' in key.lower():
                    print(f"  {key} = {value}")

            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env
            )

            self.running = True

            # 启动读写线程
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.write_thread = threading.Thread(target=self._write_loop, daemon=True)
            self.read_thread.start()
            self.write_thread.start()

            print(f"MCP服务器已启动 (PID: {self.process.pid})")

            # 等待服务器初始化
            time.sleep(2)

            # 执行MCP协议初始化
            if not self._initialize():
                print("警告: MCP协议初始化失败，但服务器已启动")
                # 仍然返回True，因为服务器进程在运行
                # 但工具调用可能会失败

            return True

        except Exception as e:
            print(f"启动MCP服务器失败: {e}")
            return False

    def stop(self):
        """停止MCP服务器"""
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        if self.read_thread:
            self.read_thread.join(timeout=2)
        if self.write_thread:
            self.write_thread.join(timeout=2)

        print("MCP服务器已停止")

    def _read_loop(self):
        """读取服务器输出的循环"""
        while self.running and self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
                self._handle_message(message)
            except json.JSONDecodeError:
                # 可能是日志输出，打印到stderr
                if line and not line.startswith('{'):
                    print(f"[MCP服务器日志] {line}", file=sys.stderr)

    def _write_loop(self):
        """向服务器发送请求的循环"""
        while self.running and self.process and self.process.stdin:
            try:
                request = self.request_queue.get(timeout=1)
                if request is None:
                    break

                json_line = json.dumps(request) + '\n'
                self.process.stdin.write(json_line)
                self.process.stdin.flush()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"发送请求失败: {e}")
                break

    def _handle_message(self, message: Dict):
        """处理收到的消息"""
        if 'id' in message:
            # 这是对某个请求的响应
            request_id = message['id']
            if request_id in self.response_map:
                self.response_map[request_id].put(message)
        else:
            # 可能是通知消息
            print(f"[MCP通知] {message}")

    def _call_tool(self, tool_name: str, arguments: Dict, retries: int = 2, timeout: int = 30) -> Optional[Dict]:
        """调用MCP工具并等待响应

        Args:
            tool_name: 工具名称
            arguments: 参数
            retries: 重试次数（默认2次）
            timeout: 每次调用的超时时间（秒，默认30秒）
        """
        if not self.running or not self.process:
            raise RuntimeError("MCP服务器未运行")

        for attempt in range(retries + 1):
            try:
                result = self._send_request(
                    "tools/call",
                    {"name": tool_name, "arguments": arguments},
                    timeout=timeout
                )

                if result is None:
                    # _send_request已经打印了错误信息
                    if attempt < retries:
                        print(f"工具调用失败，正在重试 ({attempt + 1}/{retries})...")
                        time.sleep(2 ** attempt)  # 指数退避
                        continue
                    return None

                return result

            except Exception as e:
                print(f"工具调用异常: {e}")
                if attempt < retries:
                    print(f"正在重试 ({attempt + 1}/{retries})...")
                    time.sleep(2 ** attempt)
                    continue
                return None

        return None

    def _is_retryable_error(self, error: Dict) -> bool:
        """判断错误是否可重试"""
        error_code = error.get('code', 0)
        error_message = str(error.get('message', '')).lower()

        # 网络错误、超时、服务器暂时不可用等可以重试
        retryable_codes = [-32000, -32603]  # 服务器错误、内部错误
        retryable_keywords = ['timeout', 'time out', 'network', 'connection', 'busy', 'temporarily', 'retry']

        if error_code in retryable_codes:
            return True

        for keyword in retryable_keywords:
            if keyword in error_message:
                return True

        return False

    def _is_a_share(self, symbol: str) -> bool:
        """判断是否为A股代码"""
        # 移除可能的后缀
        clean_symbol = symbol.upper()
        if '.' in clean_symbol:
            clean_symbol = clean_symbol.split('.')[0]

        # A股代码: 上海60, 68开头; 深圳00, 30开头
        return (clean_symbol.startswith(('60', '68')) or
                clean_symbol.startswith(('00', '30')))

    def _convert_symbol_to_code(self, symbol: str, format: str = "tdx") -> str:
        """
        将通用股票代码转换为MCP服务器支持的格式

        Args:
            symbol: 通用股票代码，如 "AAPL", "600519.SS", "000001.SZ", "sh000001"
            format: 目标格式，"tdx"（通达信）或 "jq"（聚宽），默认tdx

        Returns:
            转换后的代码
        """
        symbol_upper = symbol.upper()

        # 如果已经是通达信格式 (sh/sz开头)
        if symbol_upper.startswith(('SH', 'SZ')):
            return symbol_upper  # 保持原样

        # 如果已经是聚宽格式 (包含.XSHG/.XSHE)
        if '.XSHG' in symbol_upper or '.XSHE' in symbol_upper:
            if format == "jq":
                return symbol_upper
            else:
                # 聚宽转通达信
                if '.XSHG' in symbol_upper:
                    code = symbol_upper.replace('.XSHG', '')
                    return f"SH{code}"
                else:  # .XSHE
                    code = symbol_upper.replace('.XSHE', '')
                    return f"SZ{code}"

        # 处理带后缀的通用格式 (如 .SS, .SZ)
        if '.' in symbol_upper:
            code, suffix = symbol_upper.split('.')
            if suffix == 'SS' or suffix == 'SH':
                if format == "jq":
                    return f"{code}.XSHG"
                else:
                    return f"SH{code}"
            elif suffix == 'SZ':
                if format == "jq":
                    return f"{code}.XSHE"
                else:
                    return f"SZ{code}"
            else:
                # 其他后缀，如 .HK, .US 等，不转换
                return symbol_upper

        # 纯数字代码，假设是A股
        if symbol_upper.isdigit():
            # 判断市场
            if symbol_upper.startswith(('60', '68')):
                if format == "jq":
                    return f"{symbol_upper}.XSHG"
                else:
                    return f"SH{symbol_upper}"
            elif symbol_upper.startswith(('00', '30')):
                if format == "jq":
                    return f"{symbol_upper}.XSHE"
                else:
                    return f"SZ{symbol_upper}"

        # 其他情况（如美股AAPL），返回原样
        return symbol_upper

    def _parse_price_data(self, price_result: Dict, original_symbol: str) -> Optional[Dict]:
        """
        解析get_price返回的数据，转换为标准报价格式

        Args:
            price_result: get_price工具返回的原始数据
            original_symbol: 原始股票代码（用于返回）

        Returns:
            标准化的报价字典，包含 price, symbol, name, open, high, low, close, volume 等字段
        """
        if not isinstance(price_result, dict):
            return None

        # 检查是否有数据
        if 'data' not in price_result:
            return None

        data = price_result['data']
        if not isinstance(data, dict):
            return None

        records = data.get('records', [])
        columns = data.get('columns', [])

        if not records or not columns:
            return None

        # 获取最新一条记录（第一条或最后一条？假设records按时间升序排列，最后一条最新）
        latest_record = records[-1] if records else None
        if not latest_record:
            return None

        # 将列名映射到记录值
        record_dict = {}
        for i, col in enumerate(columns):
            if i < len(latest_record):
                record_dict[col] = latest_record[i]

        # 尝试提取常见字段（根据Ashare库的默认字段）
        # 常见字段名: 'open', 'high', 'low', 'close', 'volume', 'amount', 'date', 'time'
        # 也可能使用中文字段名: '开盘', '最高', '最低', '收盘', '成交量', '成交额', '日期', '时间'
        open_price = None
        high_price = None
        low_price = None
        close_price = None
        volume = None
        date_time = None

        # 尝试多种可能的字段名
        for field in ['close', '收盘', 'price']:
            if field in record_dict:
                close_price = record_dict[field]
                break

        for field in ['open', '开盘']:
            if field in record_dict:
                open_price = record_dict[field]
                break

        for field in ['high', '最高']:
            if field in record_dict:
                high_price = record_dict[field]
                break

        for field in ['low', '最低']:
            if field in record_dict:
                low_price = record_dict[field]
                break

        for field in ['volume', '成交量', 'vol']:
            if field in record_dict:
                volume = record_dict[field]
                break

        for field in ['date', '日期', 'datetime', '时间']:
            if field in record_dict:
                date_time = record_dict[field]
                break

        # 如果没有close价格，尝试使用其他价格字段
        if close_price is None:
            for field in ['open', 'high', 'low']:
                if field in record_dict:
                    close_price = record_dict[field]
                    break

        # 构建标准报价格式
        quote = {
            'symbol': original_symbol,
            'code': price_result.get('code', original_symbol),  # 服务器返回的代码
            'price': close_price,  # 最新价（使用收盘价或最新价）
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'timestamp': date_time if date_time else self._get_current_timestamp(),
            'raw_data': price_result  # 保留原始数据供调试
        }

        # 添加额外字段
        if 'message' in price_result:
            quote['message'] = price_result['message']

        return quote

    def _get_current_timestamp(self) -> str:
        """获取当前时间戳字符串"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _fallback_get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """备用数据源：使用东方财富API获取A股实时数据"""
        if not self._is_a_share(symbol):
            return None

        try:
            # 延迟导入，避免依赖问题
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            import pandas as pd
            from datetime import datetime

            # 清除所有可能的代理环境变量，避免requests库使用它们
            proxy_keys = [
                # 标准代理环境变量
                'HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy',
                'FTP_PROXY', 'ftp_proxy', 'ALL_PROXY', 'all_proxy',
                # Windows可能使用的代理设置
                'HTTP_PROXY_USER', 'HTTP_PROXY_PASS', 'HTTPS_PROXY_USER', 'HTTPS_PROXY_PASS',
                # Node.js/NPM特定代理
                'npm_config_proxy', 'npm_config_https_proxy', 'npm_config_http_proxy',
                # 其他可能的代理设置
                'PROXY', 'proxy', 'NODE_TLS_REJECT_UNAUTHORIZED',
                # 更多代理变量
                'REQUEST_PROXY', 'request_proxy', 'HTTPS_REQUEST_PROXY', 'https_request_proxy',
                'SOCKS_PROXY', 'socks_proxy', 'SOCKS5_PROXY', 'socks5_proxy',
                'WINHTTP_PROXY', 'WINHTTP_PROXY_BYPASS'
            ]
            for key in proxy_keys:
                if key in os.environ:
                    print(f"[备用数据源] 清除代理环境变量: {key}")
                    del os.environ[key]
            # 设置NO_PROXY
            os.environ['NO_PROXY'] = '*'
            os.environ['no_proxy'] = '*'
        except ImportError:
            print("[备用数据源] 缺少依赖: requests, pandas")
            return None

        # 清理股票代码
        clean_symbol = symbol.upper()
        if '.' in clean_symbol:
            clean_symbol = clean_symbol.split('.')[0]

        try:
            # 东方财富实时数据API
            # 注意：这个API可能需要验证，这里使用简化的示例
            # 实际使用时可能需要更稳定的API
            if clean_symbol.startswith(('60', '68')):
                market = 'SH'
                secid = f"1.{clean_symbol}"
            else:
                market = 'SZ'
                secid = f"0.{clean_symbol}"

            url = f"https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': secid,
                'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
                'fields': 'f43,f57,f58,f169,f170,f46,f44,f51,f168,f47,f164,f163,f116,f60,f45,f52,f50,f48,f167,f117,f71,f161,f49,f530,f135,f136,f137,f138,f139,f141,f142,f144,f145,f147,f148,f140,f143,f146,f149,f55,f62,f162,f92,f173,f104,f105,f84,f85,f183,f184,f185,f186,f187,f188,f189,f190,f191,f192,f107,f111,f86,f177,f78,f110,f262,f263,f264,f267,f268,f250,f251,f252,f253,f254,f255,f256,f257,f258,f266,f269,f270,f271,f273,f274,f275,f127,f199,f128,f193,f196,f194,f195,f197,f80,f280,f281,f282,f284,f285,f286,f287,f292',
                'invt': 2,
                'cb': 'jQuery112406115645080857178_1631234567890',
                '_': int(datetime.now().timestamp() * 1000)
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/'
            }

            # 清除代理设置，避免连接失败
            proxies = {
                'http': None,
                'https': None,
                'ftp': None
            }

            try:
                response = requests.get(url, params=params, headers=headers, timeout=10, verify=False, proxies=proxies, trust_env=False)
            except TypeError:
                # 旧版本requests不支持trust_env参数
                response = requests.get(url, params=params, headers=headers, timeout=10, verify=False, proxies=proxies)
            data = response.json()

            if 'data' not in data:
                return None

            stock_data = data['data']

            # 转换为MCP兼容格式
            result = {
                'symbol': symbol,
                'name': stock_data.get('f58', 'N/A'),  # 股票名称
                'price': stock_data.get('f43', 'N/A'),  # 最新价
                'change': stock_data.get('f170', 'N/A'),  # 涨跌额
                'changePercent': stock_data.get('f171', 'N/A'),  # 涨跌幅
                'open': stock_data.get('f46', 'N/A'),  # 开盘价
                'high': stock_data.get('f44', 'N/A'),  # 最高价
                'low': stock_data.get('f45', 'N/A'),  # 最低价
                'volume': stock_data.get('f47', 'N/A'),  # 成交量
                'amount': stock_data.get('f48', 'N/A'),  # 成交额
                'timestamp': datetime.now().isoformat()
            }

            print(f"[备用数据源] 成功获取 {symbol} 数据")
            return result

        except Exception as e:
            print(f"[备用数据源] 获取 {symbol} 数据失败: {e}")
            return None

    # 公开的API方法

    def get_stock_quote(self, symbol: str, retries: int = 2, timeout: int = 30,
                       use_fallback: bool = True, count: int = 1, frequency: str = '1d',
                       end_date: str = '', fields: List[str] = None) -> Optional[Dict]:
        """
        获取股票实时报价

        Args:
            symbol: 股票代码，如 "AAPL", "600519.SS", "sh000001", "000001.XSHG"
            retries: 重试次数（默认2次）
            timeout: 超时时间（秒，默认30秒）
            use_fallback: 是否使用备用数据源（默认True）
            count: 获取的K线数量（默认1条）
            frequency: K线周期，支持 '1m','5m','15m','30m','60m','1d','1w','1M'（默认'1d'）
            end_date: 结束日期，格式 'YYYY-MM-DD'（默认当前日期）
            fields: 返回字段列表（默认全部）

        Returns:
            股票报价信息字典，包含 price, symbol, name, open, high, low, close, volume 等字段
            如果获取多条数据，则返回最新一条的报价信息
        """
        if fields is None:
            fields = []

        # 转换股票代码格式为通达信格式（默认）
        code = self._convert_symbol_to_code(symbol, format="tdx")

        # 尝试多个可能的工具名称，支持不同的MCP服务器
        # 1. 首先尝试get_price（针对基于Ashare的新服务器）
        # 2. 然后尝试其他工具名称（针对原来的mcp-stock-analysis-server）
        tool_names = ["get_price", "stock-analysis", "getStockQuote", "stockQuote", "getQuote", "quote"]

        errors = []  # 存储错误信息

        for tool_name in tool_names:
            print(f"[MCP] 尝试工具: {tool_name}")

            # 根据不同工具构建不同的参数
            if tool_name == "get_price":
                # get_price使用新参数格式
                arguments = {
                    "code": code,
                    "end_date": end_date,
                    "count": count,
                    "frequency": frequency,
                    "fields": fields
                }
            else:
                # 其他工具可能只接受symbol参数
                arguments = {"symbol": symbol}

            result = self._call_tool(tool_name, arguments, retries=1, timeout=timeout)

            if result:
                # 检查是否是错误响应
                if isinstance(result, dict):
                    # 检查是否有isError标志或工具未找到错误
                    if result.get('isError') is True:
                        # 检查是否是工具未找到错误
                        error_text = ''
                        if 'content' in result and isinstance(result['content'], list):
                            for item in result['content']:
                                if isinstance(item, dict) and item.get('type') == 'text':
                                    error_text = item.get('text', '')
                                    break

                        if 'not found' in error_text.lower() or 'not_found' in error_text.lower():
                            print(f"[MCP] 工具 {tool_name} 未找到，尝试下一个工具")
                            errors.append((tool_name, result))
                            continue  # 工具不存在，尝试下一个
                        else:
                            print(f"[MCP] 工具 {tool_name} 返回错误: {result}")
                            errors.append((tool_name, result))
                            continue  # 其他错误，尝试下一个

                    # 尝试解析数据
                    if tool_name == "get_price":
                        parsed = self._parse_price_data(result, symbol)
                    else:
                        # 对于旧格式的工具，直接返回结果（假设已经是标准格式）
                        parsed = result

                    if parsed:
                        return parsed
                    else:
                        print(f"[MCP] 无法解析工具 {tool_name} 返回的数据格式: {result}")
                        errors.append((tool_name, result))
                else:
                    print(f"[MCP] 工具 {tool_name} 返回非字典结果: {type(result)}")
                    errors.append((tool_name, result))
            else:
                # result为None，可能是网络错误或工具不存在
                print(f"[MCP] 工具 {tool_name} 未返回结果")
                errors.append((tool_name, None))

        # 所有MCP工具都失败，尝试备用数据源（如果启用且是A股）
        if use_fallback and self._is_a_share(symbol):
            print(f"[备用] 所有MCP工具失败，尝试备用数据源获取 {symbol}...")
            fallback_result = self._fallback_get_stock_quote(symbol)
            if fallback_result:
                return fallback_result
            else:
                print(f"[备用] 备用数据源也失败")

        # 如果既不是A股，也不是有效结果，返回None
        print(f"[MCP] 所有工具尝试失败，错误列表: {errors}")
        return None

    def get_price(self, code: str, end_date: str = '', count: int = 10,
                 frequency: str = '1d', fields: List[str] = None,
                 retries: int = 2, timeout: int = 30) -> Optional[Dict]:
        """
        获取股票行情数据（直接调用get_price工具）

        Args:
            code: 证券代码，支持'sh000001'或'000001.XSHG'格式
            end_date: 结束日期，格式为'YYYY-MM-DD'
            count: 获取的K线数量
            frequency: K线周期，分钟线：'1m', '5m', '15m', '30m', '60m'，日线：'1d'，周线：'1w'，月线：'1M'
            fields: 返回字段列表，默认为空（全部）
            retries: 重试次数（默认2次）
            timeout: 超时时间（秒，默认30秒）

        Returns:
            股票数据字典，包含 code, data, message 等字段（原始get_price响应）
        """
        if fields is None:
            fields = []

        arguments = {
            "code": code,
            "end_date": end_date,
            "count": count,
            "frequency": frequency,
            "fields": fields
        }

        return self._call_tool("get_price", arguments, retries=retries, timeout=timeout)

    def get_historical_data(self, symbol: str, interval: str = "daily",
                           start_date: str = None, end_date: str = None,
                           retries: int = 2, timeout: int = 30, count: int = 100) -> Optional[Dict]:
        """
        获取股票历史数据（通过get_price工具）

        Args:
            symbol: 股票代码
            interval: 时间间隔，"daily", "weekly", "monthly"
            start_date: 开始日期，格式 "YYYY-MM-DD"（暂未使用，保留兼容性）
            end_date: 结束日期，格式 "YYYY-MM-DD"（默认当前日期）
            retries: 重试次数（默认2次）
            timeout: 超时时间（秒，默认30秒）
            count: 获取的K线数量（默认100条）

        Returns:
            历史数据字典，包含 code, data, message 等字段（原始get_price响应格式）
        """
        # 转换股票代码格式为通达信格式（默认）
        code = self._convert_symbol_to_code(symbol, format="tdx")

        # 映射interval到frequency
        interval_map = {
            "daily": "1d",
            "weekly": "1w",
            "monthly": "1M"
        }
        frequency = interval_map.get(interval.lower(), "1d")

        # 构建参数
        arguments = {
            "code": code,
            "end_date": end_date if end_date else "",
            "count": count,
            "frequency": frequency,
            "fields": []
        }

        print(f"[MCP] 调用get_price工具获取历史数据，代码: {code}, 频率: {frequency}, 数量: {count}")
        result = self._call_tool("get_price", arguments, retries=retries, timeout=timeout)

        if result and isinstance(result, dict) and 'data' in result:
            return result
        else:
            print(f"[MCP] 获取历史数据失败: {result}")
            return None

    def analyze_trend(self, symbol: str, period: int = 30, include_news: bool = True,
                     retries: int = 2, timeout: int = 30) -> Optional[Dict]:
        """
        分析股票趋势（如果服务器支持）

        Args:
            symbol: 股票代码
            period: 分析周期（天）
            include_news: 是否包含新闻情感分析
            retries: 重试次数（默认2次）
            timeout: 超时时间（秒，默认30秒）

        Returns:
            趋势分析结果（当前服务器不支持，返回None）
        """
        print(f"[警告] 当前MCP服务器不支持analyzeTrend工具，请使用get_price获取行情数据")
        return None

    def get_technical_indicators(self, symbol: str, indicator: str = "all",
                               retries: int = 2, timeout: int = 30) -> Optional[Dict]:
        """
        获取技术指标（如果服务器支持）

        Args:
            symbol: 股票代码
            indicator: 指标名称，如 "RSI", "MACD", "BOLL", "all"
            retries: 重试次数（默认2次）
            timeout: 超时时间（秒，默认30秒）

        Returns:
            技术指标数据（当前服务器不支持，返回None）
        """
        print(f"[警告] 当前MCP服务器不支持getTechnicalIndicators工具，请使用get_price获取行情数据")
        return None

    def list_tools(self, timeout: int = 10) -> Optional[List[Dict]]:
        """
        列出MCP服务器提供的所有可用工具

        Args:
            timeout: 超时时间（秒，默认10秒）

        Returns:
            工具列表，每个工具包含名称、描述等信息
        """
        try:
            # 使用MCP协议的tools/list方法
            result = self._send_request("tools/list", timeout=timeout)
            if result and 'tools' in result:
                return result['tools']
            else:
                print(f"[MCP] 工具列表响应格式异常: {result}")
                return None
        except Exception as e:
            print(f"[MCP] 获取工具列表失败: {e}")
            return None

    def get_server_info(self, timeout: int = 10) -> Optional[Dict]:
        """
        获取MCP服务器信息

        Args:
            timeout: 超时时间（秒，默认10秒）

        Returns:
            服务器信息
        """
        try:
            result = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "mcp_stock_client",
                    "version": "1.0.0"
                }
            }, timeout=timeout)
            return result
        except Exception as e:
            print(f"[MCP] 获取服务器信息失败: {e}")
            return None


# 简化版使用示例
def quick_start(symbol: str = "AAPL"):
    """
    快速开始示例：获取股票报价

    Args:
        symbol: 股票代码

    Returns:
        股票报价信息
    """
    # 方法1: 使用环境变量配置NEWS_API_KEY（如果需要新闻分析）
    env = {}
    news_api_key = os.getenv("NEWS_API_KEY")
    if news_api_key:
        env["NEWS_API_KEY"] = news_api_key
    else:
        print("提示: 设置NEWS_API_KEY环境变量以启用新闻情感分析功能")

    # 强制禁用代理
    env['NO_PROXY'] = '*'
    env['NODE_NO_HTTP_PROXY'] = '1'
    env['NODE_NO_HTTPS_PROXY'] = '1'
    env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

    client = MCPStockClient(env=env)

    try:
        # 启动服务器
        if not client.start():
            print("请确保已安装Node.js和npm，并运行: npm install -g npx")
            return None

        # 等待服务器初始化
        time.sleep(2)

        # 获取股票报价
        print(f"正在获取 {symbol} 的实时报价...")
        quote = client.get_stock_quote(symbol)

        if quote:
            print(f"股票报价: {json.dumps(quote, indent=2, ensure_ascii=False)}")
        else:
            print(f"无法获取 {symbol} 的报价")

        return quote

    finally:
        client.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP股票分析客户端")
    parser.add_argument("symbol", nargs="?", default="AAPL", help="股票代码 (默认: AAPL)")
    parser.add_argument("--interval", default="daily", help="历史数据间隔 (daily, weekly, monthly)")
    parser.add_argument("--historical", action="store_true", help="获取历史数据")
    parser.add_argument("--trend", action="store_true", help="分析趋势")

    args = parser.parse_args()

    # 简单示例
    env = {}
    news_api_key = os.getenv("NEWS_API_KEY")
    if news_api_key:
        env["NEWS_API_KEY"] = news_api_key
    # 禁用代理
    env['NO_PROXY'] = '*'
    env['NODE_NO_HTTP_PROXY'] = '1'
    env['NODE_NO_HTTPS_PROXY'] = '1'
    env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

    client = MCPStockClient(env=env)

    try:
        if not client.start():
            print("启动失败，请检查:")
            print("1. 是否安装了Node.js和npm")
            print("2. 是否可以通过 npx 运行 mcp-stock-analysis-server")
            print("3. 或者尝试: npm install -g mcp-stock-analysis-server")
            sys.exit(1)

        time.sleep(2)  # 等待服务器初始化

        if args.historical:
            print(f"获取 {args.symbol} 的历史数据...")
            data = client.get_historical_data(args.symbol, args.interval)
            if data:
                print(f"历史数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            else:
                print("获取历史数据失败")

        elif args.trend:
            print(f"分析 {args.symbol} 的趋势...")
            trend = client.analyze_trend(args.symbol)
            if trend:
                print(f"趋势分析: {json.dumps(trend, indent=2, ensure_ascii=False)}")
            else:
                print("趋势分析失败")

        else:
            print(f"获取 {args.symbol} 的实时报价...")
            quote = client.get_stock_quote(args.symbol)
            if quote:
                print(f"股票报价: {json.dumps(quote, indent=2, ensure_ascii=False)}")
            else:
                print("获取报价失败")

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        client.stop()