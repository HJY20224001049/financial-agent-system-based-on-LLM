import subprocess
import os
import sys
import json

def test_mcp_server():
    """测试MCP服务器启动和调用"""
    print("测试MCP服务器...")

    # 清除所有代理环境变量
    env = os.environ.copy()
    proxy_keys = []
    for key in env.keys():
        if 'proxy' in key.lower():
            proxy_keys.append(key)

    for key in proxy_keys:
        print(f"移除代理环境变量: {key}")
        del env[key]

    # 设置NO_PROXY
    env['NO_PROXY'] = '*'
    env['HTTP_PROXY'] = ''
    env['HTTPS_PROXY'] = ''
    env['http_proxy'] = ''
    env['https_proxy'] = ''

    # 尝试启动MCP服务器
    try:
        # 注意：这里假设npx可用
        cmd = ["npx.cmd", "-y", "mcp-stock-analysis-server"]
        print(f"执行命令: {' '.join(cmd)}")
        print(f"环境变量清理完成")

        # 启动进程
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=env
        )

        print(f"进程启动，PID: {proc.pid}")

        # 等待几秒钟
        import time
        time.sleep(3)

        # 检查进程是否还在运行
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            print(f"进程已退出，退出码: {proc.returncode}")
            print(f"标准输出:\n{stdout[:500]}")
            print(f"标准错误:\n{stderr[:500]}")
        else:
            print("进程仍在运行")
            # 发送初始化消息
            init_msg = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "id": 1,
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test_client",
                        "version": "1.0.0"
                    }
                }
            }

            try:
                proc.stdin.write(json.dumps(init_msg) + '\n')
                proc.stdin.flush()

                # 读取响应
                import threading
                import queue

                response_queue = queue.Queue()

                def read_output():
                    while True:
                        line = proc.stdout.readline()
                        if not line:
                            break
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                response_queue.put(data)
                            except:
                                print(f"非JSON输出: {line}")

                reader_thread = threading.Thread(target=read_output, daemon=True)
                reader_thread.start()

                # 等待响应
                try:
                    response = response_queue.get(timeout=5)
                    print(f"收到响应: {json.dumps(response, indent=2)}")
                except:
                    print("等待响应超时")

            except Exception as e:
                print(f"通信错误: {e}")

            # 终止进程
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except:
                proc.kill()

    except Exception as e:
        print(f"启动MCP服务器失败: {e}")
        import traceback
        traceback.print_exc()

def test_direct_http():
    """测试直接HTTP请求，检查是否有代理问题"""
    print("\n测试直接HTTP请求...")
    try:
        import requests

        # 测试几个URL
        urls = [
            "https://api.github.com",
            "https://www.google.com",
            "https://query1.finance.yahoo.com"
        ]

        for url in urls:
            try:
                print(f"请求 {url} ...")
                # 显式设置不使用代理
                response = requests.get(url, timeout=10, proxies={'http': None, 'https': None}, verify=False)
                print(f"  成功: 状态码 {response.status_code}")
            except Exception as e:
                print(f"  失败: {e}")

    except ImportError:
        print("requests模块未安装")

if __name__ == "__main__":
    test_direct_http()
    test_mcp_server()