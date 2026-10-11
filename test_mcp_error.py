import os
import sys
import time
from mcp_stock_client import MCPStockClient

def test_mcp_with_proxy_debug():
    """测试MCP客户端，添加详细的代理调试信息"""

    # 首先，打印当前环境变量
    print("当前环境变量中的代理设置:")
    for key, value in os.environ.items():
        if 'proxy' in key.lower():
            print(f"  {key} = {value}")

    if not any('proxy' in key.lower() for key in os.environ.keys()):
        print("  (无代理环境变量)")

    print("\n创建MCP客户端...")

    # 创建客户端，显式传递空的环境变量
    env = {}

    # 清除所有可能的代理变量
    proxy_keys_to_remove = []
    for key in os.environ.keys():
        if 'proxy' in key.lower():
            proxy_keys_to_remove.append(key)

    for key in proxy_keys_to_remove:
        if key in os.environ:
            print(f"从os.environ移除代理变量: {key}")
            del os.environ[key]

    client = MCPStockClient(env=env)

    print("启动MCP服务器...")
    if not client.start():
        print("启动失败")
        return

    print("等待服务器初始化...")
    time.sleep(3)

    # 测试获取股票报价
    test_symbols = ["AAPL", "600519.SS", "000001.SZ"]

    for symbol in test_symbols:
        print(f"\n尝试获取 {symbol} 的报价...")
        try:
            quote = client.get_stock_quote(symbol, use_fallback=True)

            if quote:
                print(f"成功获取 {symbol} 数据")
                if isinstance(quote, dict):
                    # 检查是否有错误标志
                    if quote.get('isError'):
                        print(f"  返回错误: {quote}")
                    else:
                        print(f"  价格: {quote.get('price', 'N/A')}")
                else:
                    print(f"  返回类型: {type(quote)}")
                    print(f"  内容: {quote[:200] if isinstance(quote, str) else quote}")
            else:
                print(f"获取 {symbol} 失败，返回None")

        except Exception as e:
            print(f"获取 {symbol} 时出错: {e}")
            import traceback
            traceback.print_exc()

    print("\n停止MCP服务器...")
    client.stop()
    print("测试完成")

if __name__ == "__main__":
    test_mcp_with_proxy_debug()