#!/usr/bin/env python
"""
测试MCP服务器的可用工具
"""
import sys
import os
import json
import time
import subprocess
import threading
import queue

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SimpleMCPTester:
    """简单的MCP协议测试器"""

    def __init__(self, server_command=None):
        if server_command is None:
            # 根据平台确定npx命令
            import platform
            is_windows = platform.system() == "Windows"
            npx_cmd = "npx.cmd" if is_windows else "npx"
            import shutil
            npx_path = shutil.which(npx_cmd)
            if npx_path:
                self.server_command = [npx_path, "-y", "mcp-stock-analysis-server"]
            else:
                self.server_command = [npx_cmd, "-y", "mcp-stock-analysis-server"]
        else:
            self.server_command = server_command

        self.process = None
        self.running = False
        self.read_thread = None
        self.write_thread = None
        self.request_queue = queue.Queue()
        self.response_map = {}
        self.next_id = 1

    def start(self):
        """启动MCP服务器"""
        try:
            # 设置npm缓存目录到用户目录
            env = os.environ.copy()
            user_cache_dir = os.path.join(os.path.expanduser('~'), '.npm-cache')
            os.makedirs(user_cache_dir, exist_ok=True)
            env['npm_config_cache'] = user_cache_dir
            self._safe_print(f"[INFO] 设置npm缓存目录: {user_cache_dir}")

            # 清除代理设置，避免连接失败
            proxy_keys = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
            for key in proxy_keys:
                if key in env:
                    self._safe_print(f"[INFO] 移除环境变量 {key}")
                    del env[key]
            # 设置NO_PROXY为所有
            env['NO_PROXY'] = '*'

            self.process = subprocess.Popen(
                self.server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并stderr到stdout
                text=False,  # 不使用文本模式，我们自己解码
                bufsize=1,
                env=env
            )

            self.running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.write_thread = threading.Thread(target=self._write_loop, daemon=True)
            self.read_thread.start()
            self.write_thread.start()

            self._safe_print(f"MCP服务器已启动 (PID: {self.process.pid})")
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

        self._safe_print("MCP服务器已停止")

    def _safe_print(self, text: str, prefix: str = ""):
        """安全打印，避免编码问题"""
        # 首先清理文本中的非ASCII字符
        def clean_text(t):
            # 移除控制字符和特殊Unicode字符
            import re
            # 替换常见的Unicode符号为ASCII等价物
            replacements = {
                '\u2705': '[OK]',
                '\u2713': '[OK]',
                '\u2714': '[OK]',
                '\u2716': '[FAIL]',
                '\u2717': '[FAIL]',
                '\u274c': '[FAIL]',
                '\u26a0': '[WARN]',
                '\u2757': '[WARN]',
            }
            for uni, ascii_repl in replacements.items():
                t = t.replace(uni, ascii_repl)
            # 对于其他非ASCII字符，尝试保留中文字符但移除特殊符号
            try:
                t.encode('gbk')
                return t  # 可以编码为gbk，没问题
            except UnicodeEncodeError:
                # 移除无法编码的字符
                return ''.join(c for c in t if ord(c) < 128 or (ord(c) >= 0x4e00 and ord(c) <= 0x9fff))

        safe_text = clean_text(str(text))
        safe_prefix = clean_text(prefix)

        try:
            print(f"{safe_prefix}{safe_text}")
        except Exception:
            # 最终备用方案：仅ASCII
            ascii_text = ''.join(c for c in f"{prefix}{text}" if ord(c) < 128)
            print(ascii_text)

    def _read_loop(self):
        """读取服务器输出的循环"""
        while self.running and self.process and self.process.stdout:
            line_bytes = self.process.stdout.readline()
            if not line_bytes:
                break

            try:
                line = line_bytes.decode('utf-8', errors='replace').strip()
            except UnicodeDecodeError:
                # 如果utf-8解码失败，尝试gbk
                try:
                    line = line_bytes.decode('gbk', errors='replace').strip()
                except UnicodeDecodeError:
                    # 最终备用方案：忽略非可解码字符
                    line = line_bytes.decode('latin-1', errors='replace').strip()

            if not line:
                continue

            try:
                message = json.loads(line)
                self._handle_message(message)
            except json.JSONDecodeError:
                # 可能是日志输出
                if line and not line.startswith('{'):
                    self._safe_print(line, "[服务器日志] ")

    def _write_loop(self):
        """向服务器发送请求的循环"""
        while self.running and self.process and self.process.stdin:
            try:
                request = self.request_queue.get(timeout=1)
                if request is None:
                    break

                json_line = json.dumps(request) + '\n'
                self.process.stdin.write(json_line.encode('utf-8'))
                self.process.stdin.flush()
            except queue.Empty:
                continue
            except Exception as e:
                self._safe_print(f"发送请求失败: {e}")
                break

    def _handle_message(self, message: dict):
        """处理收到的消息"""
        if 'id' in message:
            # 这是对某个请求的响应
            request_id = message['id']
            if request_id in self.response_map:
                self.response_map[request_id].put(message)
        else:
            # 可能是通知消息
            self._safe_print(str(message), "[服务器通知] ")

    def send_request(self, method: str, params: dict = None, timeout: int = 10):
        """发送JSON-RPC请求并等待响应"""
        if not self.running or not self.process:
            raise RuntimeError("MCP服务器未运行")

        request_id = self.next_id
        self.next_id += 1

        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }

        if params:
            request["params"] = params

        response_queue = queue.Queue()
        self.response_map[request_id] = response_queue
        self.request_queue.put(request)

        try:
            response = response_queue.get(timeout=timeout)
            return response
        except queue.Empty:
            print(f"等待响应超时: {method}")
            return None
        finally:
            self.response_map.pop(request_id, None)

def test_server_capabilities():
    """测试服务器能力"""
    print("=== MCP服务器能力测试 ===")

    tester = SimpleMCPTester()

    try:
        if not tester.start():
            print("服务器启动失败")
            return

        # 等待服务器初始化
        print("等待服务器初始化...")
        time.sleep(3)

        # 1. 测试列出可用工具
        print("\n1. 获取工具列表...")
        tools_response = tester.send_request("tools/list", timeout=15)

        if tools_response:
            print(f"工具列表响应: {json.dumps(tools_response, indent=2, ensure_ascii=False)}")

            if 'result' in tools_response and 'tools' in tools_response['result']:
                tools = tools_response['result']['tools']
                print(f"\n发现 {len(tools)} 个工具:")
                for i, tool in enumerate(tools):
                    print(f"  {i+1}. {tool.get('name', '未知')}")
                    if 'description' in tool:
                        print(f"     描述: {tool['description']}")
                    if 'inputSchema' in tool:
                        print(f"     输入参数: {json.dumps(tool['inputSchema'], ensure_ascii=False)}")
        else:
            print("无法获取工具列表")

        # 2. 测试获取资源列表
        print("\n2. 获取资源列表...")
        resources_response = tester.send_request("resources/list", timeout=15)

        if resources_response:
            print(f"资源列表响应: {json.dumps(resources_response, indent=2, ensure_ascii=False)}")
        else:
            print("无法获取资源列表")

        # 3. 测试可能的不同工具名称
        print("\n3. 测试可能的股票查询工具...")

        possible_tool_names = [
            "stock-analysis",  # 首先尝试已知的工具名称
            "getStockQuote",
            "stockQuote",
            "getQuote",
            "get_stock_quote",
            "stock_quote",
            "get_stock",
            "stock_data",
            "getStockData",
            "get_stock_data",
            "quote"
        ]

        for tool_name in possible_tool_names:
            print(f"  测试工具: {tool_name}...")
            test_response = tester.send_request("tools/call", {
                "name": tool_name,
                "arguments": {"symbol": "AAPL"}
            }, timeout=10)

            if test_response:
                if 'error' in test_response:
                    error_msg = test_response['error'].get('message', '未知错误')
                    print(f"    结果: 错误 - {error_msg}")
                    continue  # 继续尝试下一个工具
                else:
                    result = test_response.get('result', {})
                    if result.get('isError'):
                        error_text = ""
                        for content in result.get('content', []):
                            if content.get('type') == 'text':
                                error_text = content.get('text', '')
                                break
                        print(f"    结果: 工具错误 - {error_text[:100]}")
                        continue
                    else:
                        print(f"    结果: 成功!")
                        # 只打印部分结果，避免输出过长
                        content_preview = ""
                        for item in result.get('content', []):
                            if item.get('type') == 'text':
                                text = item.get('text', '')
                                content_preview = text[:200] + "..." if len(text) > 200 else text
                                break
                        print(f"    预览: {content_preview}")
                        break  # 找到可用的工具，停止测试
            else:
                print(f"    结果: 无响应")

        # 4. 测试实际的stock-analysis工具
        print("\n4. 测试stock-analysis工具...")
        stock_analysis_response = tester.send_request("tools/call", {
            "name": "stock-analysis",
            "arguments": {"symbol": "AAPL"}
        }, timeout=30)

        if stock_analysis_response:
            if 'error' in stock_analysis_response:
                error_msg = stock_analysis_response['error'].get('message', '未知错误')
                print(f"工具调用错误: {error_msg}")
            else:
                result = stock_analysis_response.get('result', {})
                if result.get('isError'):
                    print(f"工具返回错误: {result}")
                else:
                    print(f"工具调用成功!")
                    content = result.get('content', [])
                    for item in content:
                        if item.get('type') == 'text':
                            text = item.get('text', '')
                            print(f"文本内容: {text[:500]}...")
                        else:
                            print(f"其他类型内容: {item}")
        else:
            print("工具调用无响应")

        # 5. 测试多个股票代码
        print("\n5. 测试多个股票代码...")
        test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "INVALID"]
        for symbol in test_symbols:
            print(f"  测试股票代码: {symbol}...")
            response = tester.send_request("tools/call", {
                "name": "stock-analysis",
                "arguments": {"symbol": symbol}
            }, timeout=15)

            if response:
                if 'error' in response:
                    error_msg = response['error'].get('message', '未知错误')
                    print(f"    结果: 错误 - {error_msg}")
                else:
                    result = response.get('result', {})
                    if result.get('isError'):
                        error_text = ""
                        for content in result.get('content', []):
                            if content.get('type') == 'text':
                                error_text = content.get('text', '')
                                break
                        print(f"    结果: 工具错误 - {error_text[:100]}")
                    else:
                        print(f"    结果: 成功!")
                        # 提取简要信息
                        for item in result.get('content', []):
                            if item.get('type') == 'text':
                                text = item.get('text', '')
                                if "失败" in text or "错误" in text:
                                    print(f"    信息: {text[:100]}...")
                                else:
                                    print(f"    信息: 获取到数据")
                                break
            else:
                print(f"    结果: 无响应")
            time.sleep(1)  # 避免请求过快

        # 6. 测试简单查询
        print("\n6. 测试简单查询...")
        simple_query = tester.send_request("query", {"query": "AAPL stock price"}, timeout=15)

        if simple_query:
            print(f"查询响应: {json.dumps(simple_query, indent=2, ensure_ascii=False)}")
        else:
            print("查询无响应")

    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        tester.stop()

def test_direct_npx():
    """直接测试npx命令"""
    print("\n=== 直接测试npx命令 ===")

    import platform
    is_windows = platform.system() == "Windows"
    npx_cmd = "npx.cmd" if is_windows else "npx"

    # 安全打印函数
    def safe_print(text: str, prefix: str = ""):
        """安全打印，避免编码问题"""
        # 首先清理文本中的非ASCII字符
        def clean_text(t):
            # 移除控制字符和特殊Unicode字符
            import re
            # 替换常见的Unicode符号为ASCII等价物
            replacements = {
                '\u2705': '[OK]',
                '\u2713': '[OK]',
                '\u2714': '[OK]',
                '\u2716': '[FAIL]',
                '\u2717': '[FAIL]',
                '\u274c': '[FAIL]',
                '\u26a0': '[WARN]',
                '\u2757': '[WARN]',
            }
            for uni, ascii_repl in replacements.items():
                t = t.replace(uni, ascii_repl)
            # 对于其他非ASCII字符，尝试保留中文字符但移除特殊符号
            try:
                t.encode('gbk')
                return t  # 可以编码为gbk，没问题
            except UnicodeEncodeError:
                # 移除无法编码的字符
                return ''.join(c for c in t if ord(c) < 128 or (ord(c) >= 0x4e00 and ord(c) <= 0x9fff))
        safe_text = clean_text(str(text))
        safe_prefix = clean_text(prefix)
        try:
            print(f"{safe_prefix}{safe_text}")
        except Exception:
            # 最终备用方案：仅ASCII
            ascii_text = ''.join(c for c in f"{prefix}{text}" if ord(c) < 128)
            print(ascii_text)

    # 测试服务器帮助
    safe_print("测试: npx -y mcp-stock-analysis-server --help")
    try:
        result = subprocess.run(
            [npx_cmd, "-y", "mcp-stock-analysis-server", "--help"],
            capture_output=True,
            text=False,  # 不自动解码
            timeout=30
        )

        safe_print(f"返回码: {result.returncode}")
        # 手动解码输出
        if result.stdout:
            try:
                stdout_text = result.stdout.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                stdout_text = result.stdout.decode('gbk', errors='replace')
            safe_print(f"输出:\n{stdout_text[:500]}...")
        if result.stderr:
            try:
                stderr_text = result.stderr.decode('utf-8', errors='replace')
            except UnicodeDecodeError:
                stderr_text = result.stderr.decode('gbk', errors='replace')
            safe_print(f"错误:\n{stderr_text[:500]}...")

    except subprocess.SubprocessError as e:
        safe_print(f"子进程错误: {e}")
    except Exception as e:
        safe_print(f"命令执行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("MCP服务器工具测试脚本")
    print("=" * 60)

    test_direct_npx()
    test_server_capabilities()

    print("\n" + "=" * 60)
    print("测试完成")