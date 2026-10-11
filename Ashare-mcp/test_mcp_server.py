#!/usr/bin/env python3
"""
测试 MCP 服务器通信
"""
import subprocess
import json
import time
import sys
import os

def test_mcp_server():
    """测试MCP服务器通信"""
    print("启动 MCP 服务器测试...")
    print("=" * 60)

    # 启动MCP服务器作为子进程
    cmd = [sys.executable, "-m", "ashare_mcp", "--stdio"]
    print(f"启动命令: {' '.join(cmd)}")

    try:
        # 启动子进程
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # 给服务器一点时间启动
        time.sleep(0.5)

        # 发送初始化请求
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "MCP Test Client",
                    "version": "1.0.0"
                }
            }
        }

        print("\n1. 发送初始化请求...")
        print(f"请求: {json.dumps(init_request, ensure_ascii=False)}")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # 读取响应
        response = proc.stdout.readline().strip()
        print(f"响应: {response}")

        # 发送工具列表请求
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        print("\n2. 发送工具列表请求...")
        print(f"请求: {json.dumps(list_request, ensure_ascii=False)}")
        proc.stdin.write(json.dumps(list_request) + "\n")
        proc.stdin.flush()

        # 读取响应
        response = proc.stdout.readline().strip()
        print(f"响应: {response}")

        # 解析响应以获取可用工具
        try:
            list_response = json.loads(response)
            tools = list_response.get('result', {}).get('tools', [])
            print(f"\n可用工具: {len(tools)} 个")
            for tool in tools:
                print(f"  - {tool.get('name')}: {tool.get('description')}")

            # 如果找到get_price工具，测试调用它
            tool_names = [tool.get('name') for tool in tools]
            if 'get_price' in tool_names:
                print("\n3. 测试调用 get_price 工具...")
                call_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "get_price",
                        "arguments": {
                            "code": "sh000001",
                            "count": 2,
                            "frequency": "1d"
                        }
                    }
                }

                print(f"请求: {json.dumps(call_request, ensure_ascii=False)}")
                proc.stdin.write(json.dumps(call_request) + "\n")
                proc.stdin.flush()

                # 读取响应
                response = proc.stdout.readline().strip()
                print(f"响应长度: {len(response)} 字符")
                print(f"响应预览: {response[:200]}...")

                # 解析响应
                try:
                    call_response = json.loads(response)
                    result = call_response.get('result', {})
                    if result:
                        print("✓ 成功调用工具")
                        # 可以进一步解析结果内容
                    else:
                        error = call_response.get('error', {})
                        print(f"✗ 工具调用失败: {error.get('message')}")
                except json.JSONDecodeError as e:
                    print(f"✗ 解析响应失败: {e}")
        except json.JSONDecodeError as e:
            print(f"✗ 解析工具列表响应失败: {e}")

        # 发送关闭请求
        print("\n4. 发送关闭请求...")
        shutdown_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "shutdown"
        }
        proc.stdin.write(json.dumps(shutdown_request) + "\n")
        proc.stdin.flush()

        # 等待进程结束
        time.sleep(0.5)
        proc.terminate()
        proc.wait()

        print("\n" + "=" * 60)
        print("MCP 服务器测试完成!")
        return True

    except Exception as e:
        print(f"\n测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 设置Windows控制台编码
    if sys.platform == "win32":
        os.system("chcp 65001 > nul")

    success = test_mcp_server()
    sys.exit(0 if success else 1)