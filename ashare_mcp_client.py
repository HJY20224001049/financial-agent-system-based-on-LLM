"""
Ashare MCP Client
用于与 ashare_mcp MCP服务器交互的Python客户端
基于 FastMCP 的股票行情数据服务
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
import asyncio
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

class AshareMCPClient:
    """Ashare MCP客户端

    通过子进程与 ashare_mcp 服务器通信
    使用MCP协议(JSON-RPC over stdio)
    """

    def __init__(self, server_command: List[str] = None, env: Dict[str, str] = None):
        """
        初始化Ashare MCP客户端

        Args:
            server_command: 启动MCP服务器的命令，默认使用当前Python解释器运行 ashare_mcp --stdio
            env: 环境变量
        """
        if server_command is None:
            # 使用当前Python解释器，确保环境一致性
            import sys
            python_path = sys.executable
            self.server_command = [python_path, "-m", "ashare_mcp", "--stdio"]
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

    def start(self):
        """启动MCP服务器子进程"""
        try:
            # 合并环境变量
            env = os.environ.copy()
            env.update(self.env)

            # 添加Python路径，确保可以找到ashare_mcp模块
            # 假设ashare_mcp已安装或位于PYTHONPATH中

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

            print(f"Ashare MCP服务器已启动 (PID: {self.process.pid})")
            return True

        except Exception as e:
            print(f"启动Ashare MCP服务器失败: {e}")
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

        print("Ashare MCP服务器已停止")

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
                    print(f"[Ashare MCP服务器日志] {line}", file=sys.stderr)

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
            print(f"[Ashare MCP通知] {message}")

    def _call_tool(self, tool_name: str, arguments: Dict, retries: int = 2, timeout: int = 30) -> Optional[Dict]:
        """调用MCP工具并等待响应

        Args:
            tool_name: 工具名称
            arguments: 参数
            retries: 重试次数（默认2次）
            timeout: 每次调用的超时时间（秒，默认30秒）
        """
        if not self.running or not self.process:
            raise RuntimeError("Ashare MCP服务器未运行")

        for attempt in range(retries + 1):
            request_id = self.next_id
            self.next_id += 1

            request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": request_id
            }

            response_queue = queue.Queue()
            self.response_map[request_id] = response_queue
            self.request_queue.put(request)

            try:
                # 等待响应，可配置超时时间
                response = response_queue.get(timeout=timeout)

                if 'error' in response:
                    print(f"工具调用错误: {response['error']}")
                    if attempt < retries and self._is_retryable_error(response['error']):
                        print(f"正在重试 ({attempt + 1}/{retries})...")
                        continue
                    return None

                return response.get('result', {})

            except queue.Empty:
                print(f"等待工具响应超时: {tool_name} (尝试 {attempt + 1}/{retries + 1})")
                if attempt < retries:
                    print(f"等待{2 ** attempt}秒后重试...")
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                return None
            finally:
                self.response_map.pop(request_id, None)

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

    # 公开的API方法

    def get_price(self, code: str, end_date: str = '', count: int = 10,
                 frequency: str = '1d', fields: List[str] = None,
                 retries: int = 2, timeout: int = 30) -> Optional[Dict]:
        """
        获取股票行情数据

        Args:
            code: 证券代码，如'sh000001'或'000001.XSHG'
            end_date: 结束日期，格式为'YYYY-MM-DD'
            count: 获取的K线数量
            frequency: K线周期，分钟线：'1m', '5m', '15m', '30m', '60m'，日线：'1d'，周线：'1w'，月线：'1M'
            fields: 返回字段列表，默认为空（全部）
            retries: 重试次数（默认2次）
            timeout: 超时时间（秒，默认30秒）

        Returns:
            股票数据字典，包含 code, data, message 等字段
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

    def get_price_simple(self, code: str, count: int = 10, frequency: str = '1d') -> Optional[Dict]:
        """
        简化版获取股票数据（使用默认参数）

        Args:
            code: 证券代码
            count: K线数量
            frequency: K线周期

        Returns:
            股票数据字典
        """
        return self.get_price(code, count=count, frequency=frequency)

    def get_daily_data(self, code: str, count: int = 100) -> Optional[Dict]:
        """
        获取日线数据（便捷方法）

        Args:
            code: 证券代码
            count: 天数

        Returns:
            日线数据字典
        """
        return self.get_price(code, count=count, frequency='1d')

    def get_minute_data(self, code: str, count: int = 100, minute_interval: str = '5m') -> Optional[Dict]:
        """
        获取分钟线数据（便捷方法）

        Args:
            code: 证券代码
            count: K线数量
            minute_interval: 分钟间隔 '1m', '5m', '15m', '30m', '60m'

        Returns:
            分钟线数据字典
        """
        return self.get_price(code, count=count, frequency=minute_interval)


# 简化版使用示例
def quick_start(symbol: str = "sh000001"):
    """
    快速开始示例：获取股票数据

    Args:
        symbol: 股票代码

    Returns:
        股票数据信息
    """
    client = AshareMCPClient()

    try:
        # 启动服务器
        if not client.start():
            print("请确保已安装ashare_mcp模块: pip install ashare_mcp 或设置PYTHONPATH")
            return None

        # 等待服务器初始化
        time.sleep(2)

        # 获取股票数据
        print(f"正在获取 {symbol} 的日线数据...")
        data = client.get_daily_data(symbol, count=5)

        if data:
            print(f"股票数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"无法获取 {symbol} 的数据")

        return data

    finally:
        client.stop()


if __name__ == "__main__":
    import sys
    import os
    if sys.platform == "win32":
        os.system("chcp 65001 > nul")
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    import argparse

    parser = argparse.ArgumentParser(description="Ashare MCP客户端")
    parser.add_argument("symbol", nargs="?", default="sh000001", help="股票代码 (默认: sh000001)")
    parser.add_argument("--count", type=int, default=10, help="K线数量 (默认: 10)")
    parser.add_argument("--frequency", default="1d", help="K线周期 (默认: 1d)")
    parser.add_argument("--end-date", default="", help="结束日期 YYYY-MM-DD")

    args = parser.parse_args()

    # 尝试直接调用ashare_mcp模块，避免MCP通信问题
    try:
        # 添加本地Ashare-mcp目录到sys.path
        ashare_path = os.path.join(os.path.dirname(__file__), "..", "..", "Ashare-mcp")
        if os.path.exists(ashare_path):
            sys.path.insert(0, ashare_path)

        from ashare_mcp.server import get_price

        async def fetch_data():
            result = await get_price(
                code=args.symbol,
                end_date=args.end_date,
                count=args.count,
                frequency=args.frequency
            )
            return result

        print(f"直接获取 {args.symbol} 的数据...")
        result = asyncio.run(fetch_data())

        if result and result.data:
            # 转换为字典格式，与MCP客户端输出一致
            output = {
                "code": result.code,
                "data": result.data,
                "message": result.message
            }
            print(f"股票数据: {json.dumps(output, indent=2, ensure_ascii=False, default=str)}")
        else:
            print("获取数据失败")

    except ImportError as e:
        print(f"导入ashare_mcp模块失败: {e}")
        print("请确保已安装ashare_mcp模块或设置正确的PYTHONPATH")
        sys.exit(1)
    except Exception as e:
        print(f"获取数据时出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)