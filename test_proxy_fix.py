#!/usr/bin/env python3
"""
测试代理问题修复
"""
import os
import sys
import subprocess
import time
import json

def test_proxy_env():
    """测试当前代理环境变量"""
    print("当前代理相关环境变量:")
    for key, value in os.environ.items():
        if 'proxy' in key.lower():
            print(f"  {key} = {value}")

    # 检查npm配置
    print("\n检查npm配置...")
    try:
        result = subprocess.run("npm config list", shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("npm配置输出 (前1000字符):")
            print(result.stdout[:1000])
    except Exception as e:
        print(f"npm配置检查失败: {e}")

def test_direct_connection():
    """测试直接连接"""
    print("\n测试直接连接...")
    import urllib.request
    import ssl

    test_urls = [
        "https://finance.yahoo.com",
        "https://www.baidu.com",
        "https://query1.finance.yahoo.com"
    ]

    for url in test_urls:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            # 显式设置不使用代理
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

            response = urllib.request.urlopen(req, timeout=10, context=ctx)
            print(f"✅ {url}: 连接成功 (状态: {response.status})")
        except Exception as e:
            print(f"❌ {url}: 连接失败 - {type(e).__name__}: {e}")

def test_mcp_server_start():
    """测试MCP服务器启动"""
    print("\n测试MCP服务器启动...")

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
    env['NODE_NO_HTTP_PROXY'] = '1'
    env['NODE_NO_HTTPS_PROXY'] = '1'
    env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'

    # 启动MCP服务器
    try:
        cmd = ["npx.cmd", "-y", "mcp-stock-analysis-server"]
        print(f"执行命令: {' '.join(cmd)}")

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
        time.sleep(3)

        # 检查进程是否还在运行
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            print(f"进程已退出，退出码: {proc.returncode}")
            print(f"标准输出 (前500字符):\n{stdout[:500]}")
            print(f"标准错误 (前500字符):\n{stderr[:500]}")
            return False
        else:
            print("进程仍在运行，正在终止...")
            proc.terminate()
            proc.wait(timeout=5)
            return True
    except Exception as e:
        print(f"启动MCP服务器失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("代理问题诊断")
    print("="*50)

    test_proxy_env()
    test_direct_connection()
    test_mcp_server_start()

    print("\n" + "="*50)
    print("诊断完成")

if __name__ == "__main__":
    main()