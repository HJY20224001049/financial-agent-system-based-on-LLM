#!/usr/bin/env python3
"""
测试MCP代理问题诊断
"""

import os
import subprocess
import sys
import platform

def check_system_proxy():
    """检查系统代理设置"""
    print("=== 系统代理设置检查 ===")

    # 检查环境变量
    proxy_vars = []
    for key, value in os.environ.items():
        if 'proxy' in key.lower():
            proxy_vars.append((key, value))

    if proxy_vars:
        print(f"发现 {len(proxy_vars)} 个代理相关环境变量:")
        for key, value in proxy_vars:
            print(f"  {key} = {value}")
    else:
        print("未发现代理环境变量")

    # 检查Windows注册表代理设置
    if platform.system() == "Windows":
        print("\n=== Windows系统代理检查 ===")
        try:
            import winreg
            # 检查Internet设置中的代理
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
                proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                print(f"Windows系统代理启用: {proxy_enable}")
                if proxy_enable and proxy_server:
                    print(f"Windows系统代理服务器: {proxy_server}")
            except FileNotFoundError:
                print("Windows注册表中未找到代理设置")
            except Exception as e:
                print(f"读取Windows注册表错误: {e}")
        except ImportError:
            print("无法导入winreg模块（非Windows系统）")

def check_npm_config():
    """检查npm配置"""
    print("\n=== npm配置检查 ===")

    # 运行npm config list
    try:
        result = subprocess.run("npm config list", shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("npm配置:")
            print(result.stdout[:2000])  # 限制输出长度
        else:
            print(f"npm配置检查失败: {result.stderr}")
    except Exception as e:
        print(f"运行npm config list失败: {e}")

def check_npmrc_files():
    """检查npmrc配置文件"""
    print("\n=== npmrc文件检查 ===")

    # 检查可能的npmrc文件位置
    npmrc_paths = [
        os.path.join(os.path.expanduser("~"), ".npmrc"),  # 用户目录
        os.path.join(os.environ.get('APPDATA', ''), "npmrc"),  # Windows AppData
        ".npmrc",  # 当前目录
    ]

    for path in npmrc_paths:
        if os.path.exists(path):
            print(f"找到npmrc文件: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"内容预览 (前500字符):")
                    print(content[:500])
                    if 'proxy' in content.lower():
                        print("⚠️  注意: 文件中包含proxy配置")
            except Exception as e:
                print(f"读取文件失败: {e}")
        else:
            print(f"未找到npmrc文件: {path}")

def check_node_proxy_libs():
    """检查Node.js代理相关库"""
    print("\n=== Node.js全局包检查 ===")

    # 检查是否安装了全局代理相关包
    packages_to_check = [
        "global-agent",
        "global-tunnel-agent",
        "proxy-agent",
        "https-proxy-agent"
    ]

    for package in packages_to_check:
        try:
            result = subprocess.run(f"npm list -g {package}", shell=True, capture_output=True, text=True, timeout=10)
            if "empty" not in result.stdout and package in result.stdout:
                print(f"⚠️  发现全局包: {package}")
                # 提取版本信息
                for line in result.stdout.split('\n'):
                    if package in line and '@' in line:
                        print(f"    版本: {line.strip()}")
            else:
                print(f"未找到全局包: {package}")
        except Exception as e:
            print(f"检查包 {package} 失败: {e}")

def test_direct_connection():
    """测试直接连接"""
    print("\n=== 网络连接测试 ===")

    test_urls = [
        "https://finance.yahoo.com",
        "https://www.baidu.com",
        "https://quote.eastmoney.com"
    ]

    for url in test_urls:
        try:
            import urllib.request
            import ssl

            # 创建不验证SSL的context
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

            # 设置代理为空
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

            response = urllib.request.urlopen(req, timeout=10, context=ctx)
            print(f"✅ {url}: 连接成功 (状态: {response.status})")
        except Exception as e:
            print(f"❌ {url}: 连接失败 - {type(e).__name__}: {e}")

def main():
    print("MCP代理问题诊断工具")
    print("=" * 50)

    check_system_proxy()
    check_npm_config()
    check_npmrc_files()
    check_node_proxy_libs()
    test_direct_connection()

    print("\n" + "=" * 50)
    print("诊断完成")
    print("\n建议:")
    print("1. 如果发现代理配置，请清理相关配置文件")
    print("2. 检查npm全局包，移除不需要的代理相关包")
    print("3. 考虑修改MCP客户端，强制设置代理为direct://")
    print("4. 或者在MCP服务器命令中添加代理禁用参数")

if __name__ == "__main__":
    main()