#!/usr/bin/env python
"""
测试MCP修复效果
"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp_stock_client import MCPStockClient
except ImportError as e:
    print(f"导入失败: {e}")
    sys.exit(1)

def test_mcp_start():
    """测试MCP服务器启动"""
    print("=== 测试MCP服务器启动 ===")

    client = MCPStockClient()

    try:
        print("启动服务器...")
        start_time = time.time()
        if client.start():
            print(f"启动成功，耗时: {time.time() - start_time:.2f}秒")
            print("等待服务器初始化...")
            time.sleep(3)

            # 测试获取AAPL报价
            print("\n测试获取AAPL报价...")
            test_start = time.time()
            quote = client.get_stock_quote("AAPL", retries=1, timeout=15)
            test_time = time.time() - test_start

            if quote:
                print(f"成功获取报价，耗时: {test_time:.2f}秒")
                print(f"数据: {quote}")
            else:
                print(f"获取报价失败，耗时: {test_time:.2f}秒")
        else:
            print("启动失败")

    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        print("\n停止服务器...")
        client.stop()

def test_a_shares():
    """测试A股数据（备用数据源测试）"""
    print("\n=== 测试A股数据 ===")

    # A股代码示例
    test_symbols = ["600519", "000001", "300750"]

    client = MCPStockClient()

    try:
        if not client.start():
            print("MCP服务器启动失败，跳过测试")
            return

        time.sleep(2)

        for symbol in test_symbols:
            # 尝试SS后缀（上海）
            if symbol.startswith(('60', '68')):
                symbol_with_suffix = f"{symbol}.SS"
            else:
                symbol_with_suffix = f"{symbol}.SZ"

            print(f"\n测试 {symbol} ({symbol_with_suffix})...")
            start_time = time.time()
            quote = client.get_stock_quote(symbol_with_suffix, retries=1, timeout=20)
            elapsed = time.time() - start_time

            if quote:
                print(f"  成功，耗时: {elapsed:.2f}秒")
                print(f"  价格: {quote.get('price', 'N/A')}")
                print(f"  名称: {quote.get('name', 'N/A')}")
            else:
                print(f"  失败，耗时: {elapsed:.2f}秒")

    except Exception as e:
        print(f"测试A股时出错: {e}")
    finally:
        client.stop()

def check_npm_config():
    """检查npm配置"""
    print("\n=== 检查npm配置 ===")

    import subprocess

    # 检查npm缓存目录
    try:
        result = subprocess.run("npm config get cache", shell=True, capture_output=True, text=True)
        print(f"npm缓存目录: {result.stdout.strip()}")
    except Exception as e:
        print(f"检查npm配置失败: {e}")

    # 检查用户目录权限
    user_dir = os.path.expanduser('~')
    print(f"用户目录: {user_dir}")
    print(f"用户目录可写: {os.access(user_dir, os.W_OK)}")

    # 检查.npm-cache目录
    npm_cache_user = os.path.join(user_dir, '.npm-cache')
    print(f"用户npm缓存目录: {npm_cache_user}")
    print(f"目录存在: {os.path.exists(npm_cache_user)}")
    if os.path.exists(npm_cache_user):
        print(f"目录可写: {os.access(npm_cache_user, os.W_OK)}")

if __name__ == "__main__":
    print("MCP修复测试脚本")
    print("=" * 50)

    check_npm_config()
    test_mcp_start()
    test_a_shares()

    print("\n" + "=" * 50)
    print("测试完成")