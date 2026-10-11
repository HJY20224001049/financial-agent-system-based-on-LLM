#!/usr/bin/env python
"""
测试MCP客户端修复验证
验证实时数据查询和备用数据源是否正常工作
"""

import sys
import os
import time

# 添加当前目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_mcp_realtime():
    """测试MCP实时数据查询"""
    print("=== 测试MCP实时数据查询 ===")

    try:
        from mcp_stock_client import MCPStockClient

        print("1. 创建MCP客户端...")
        client = MCPStockClient()

        print("2. 启动MCP服务器...")
        if not client.start():
            print("  ❌ 启动MCP服务器失败")
            return False

        # 等待服务器初始化
        print("3. 等待服务器初始化...")
        time.sleep(3)

        # 测试美股AAPL
        print("4. 测试美股AAPL...")
        quote = client.get_stock_quote("AAPL", use_fallback=False)

        if quote:
            print(f"  ✅ 成功获取AAPL数据")
            print(f"    价格: {quote.get('price', 'N/A')}")
            print(f"    名称: {quote.get('name', 'N/A')}")
            print(f"    涨跌: {quote.get('changePercent', 'N/A')}%")
            aapl_success = True
        else:
            print("  ❌ 获取AAPL数据失败")
            aapl_success = False

        # 测试A股600519.SS
        print("5. 测试A股600519.SS...")
        quote_sh = client.get_stock_quote("600519.SS", use_fallback=False)

        if quote_sh:
            print(f"  ✅ 成功获取600519.SS数据")
            print(f"    价格: {quote_sh.get('price', 'N/A')}")
            print(f"    名称: {quote_sh.get('name', 'N/A')}")
            print(f"    涨跌: {quote_sh.get('changePercent', 'N/A')}%")
            sh_success = True
        else:
            print("  ❌ 获取600519.SS数据失败")
            sh_success = False

        print("6. 停止MCP服务器...")
        client.stop()

        return aapl_success or sh_success

    except Exception as e:
        print(f"  ❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_source():
    """测试备用数据源（东方财富API）"""
    print("\n=== 测试备用数据源 ===")

    try:
        from mcp_stock_client import MCPStockClient

        print("1. 创建MCP客户端（用于备用数据源测试）...")
        client = MCPStockClient()

        # 直接测试备用数据源（不启动MCP服务器）
        print("2. 测试A股600519.SS备用数据源...")

        # 调用内部方法测试备用数据源
        try:
            # 使用反射调用私有方法
            import inspect
            fallback_result = client._fallback_get_stock_quote("600519.SS")

            if fallback_result:
                print(f"  ✅ 备用数据源成功获取600519.SS数据")
                print(f"    价格: {fallback_result.get('price', 'N/A')}")
                print(f"    名称: {fallback_result.get('name', 'N/A')}")
                print(f"    涨跌: {fallback_result.get('changePercent', 'N/A')}%")
                print(f"    更新时间: {fallback_result.get('timestamp', 'N/A')}")
                return True
            else:
                print("  ❌ 备用数据源获取失败")
                return False

        except Exception as e:
            print(f"  ❌ 测试备用数据源出错: {e}")
            return False

    except Exception as e:
        print(f"  ❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ashare_mcp():
    """测试Ashare MCP历史数据"""
    print("\n=== 测试Ashare MCP历史数据 ===")

    try:
        from ashare_mcp_client import AshareMCPClient

        print("1. 创建Ashare MCP客户端...")
        client = AshareMCPClient()

        print("2. 启动Ashare MCP服务器...")
        if not client.start():
            print("  ❌ 启动Ashare MCP服务器失败")
            print("  请确保已安装ashare_mcp模块: pip install git+https://github.com/RusianHu/Ashare-mcp.git")
            return False

        # 等待服务器初始化
        print("3. 等待服务器初始化...")
        time.sleep(2)

        # 测试上证指数sh000001
        print("4. 测试上证指数sh000001...")
        data = client.get_price("sh000001", count=5, frequency="1d")

        if data and data.get('data') and data['data'].get('records'):
            print(f"  ✅ 成功获取sh000001历史数据")
            records = data['data']['records']
            print(f"    获取到 {len(records)} 条记录")
            # 显示最新一条数据
            if records:
                latest = records[0]
                print(f"    最新数据:")
                print(f"      时间: {latest.get('time', 'N/A')}")
                print(f"      收盘价: {latest.get('close', 'N/A')}")
                print(f"      成交量: {latest.get('volume', 'N/A')}")
            return True
        else:
            print("  ❌ 获取sh000001历史数据失败")
            if data and data.get('message'):
                print(f"    错误信息: {data['message']}")
            return False

    except ImportError:
        print("  ❌ Ashare MCP客户端导入失败")
        print("  请确保ashare_mcp_client.py在项目目录中")
        return False
    except Exception as e:
        print(f"  ❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("MCP客户端修复验证测试")
    print("=" * 60)

    results = {}

    # 测试MCP实时数据
    results['mcp_realtime'] = test_mcp_realtime()

    # 测试备用数据源
    results['fallback_source'] = test_fallback_source()

    # 测试Ashare MCP
    results['ashare_mcp'] = test_ashare_mcp()

    print("\n" + "=" * 60)
    print("测试结果汇总:")
    print("=" * 60)

    for test_name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name}: {status}")

    # 提供修复建议
    print("\n修复建议:")

    if not results['mcp_realtime']:
        print("1. MCP实时数据查询失败:")
        print("   - 确保已安装Node.js和npm")
        print("   - 运行: npx mcp-stock-analysis-server --help 测试服务器是否可用")
        print("   - 检查网络连接，确保可以访问外部API")

    if not results['fallback_source']:
        print("2. 备用数据源失败:")
        print("   - 检查网络连接，确保可以访问东方财富API")
        print("   - 检查是否安装了requests和pandas库")
        print("   - 尝试运行: pip install requests pandas")
        print("   - 可能是API限制，请稍后重试")

    if not results['ashare_mcp']:
        print("3. Ashare MCP历史数据失败:")
        print("   - 确保已安装ashare_mcp模块:")
        print("     pip install git+https://github.com/RusianHu/Ashare-mcp.git")
        print("   - 检查Python环境是否正确")

    print("\n下一步:")
    print("- 运行 run_app.bat 测试完整的应用程序")
    print("- 如果仍有问题，请检查日志中的详细错误信息")

    return all(results.values())

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n未处理的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)