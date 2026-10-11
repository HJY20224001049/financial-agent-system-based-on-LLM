"""
MCP股票分析集成示例
演示如何将mcp-stock-analysis-server集成到现有股票预测项目中
"""

import sys
import os
import subprocess
import time

# 添加当前目录到路径以便导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp_stock_client import MCPStockClient, quick_start
except ImportError:
    print("请确保 mcp_stock_client.py 在同一目录下")
    sys.exit(1)


def example_basic_usage():
    """基本使用示例"""
    print("=== MCP股票分析基本使用示例 ===\n")

    # 方法1: 快速开始函数
    print("1. 使用 quick_start() 函数:")
    quote = quick_start("AAPL")
    if quote:
        print(f"成功获取AAPL报价\n")

    # 方法2: 使用客户端类（更灵活）
    print("2. 使用 MCPStockClient 类:")

    # 设置环境变量（如果需要新闻分析）
    env = {}
    if "NEWS_API_KEY" in os.environ:
        env["NEWS_API_KEY"] = os.environ["NEWS_API_KEY"]
    else:
        print("提示: 设置 NEWS_API_KEY 环境变量以启用新闻情感分析")

    client = MCPStockClient(env=env)

    try:
        if client.start():
            # 等待服务器初始化
            time.sleep(2)

            # 示例1: 获取A股股票数据
            print("\n获取贵州茅台(600519.SS)实时报价:")
            quote_600519 = client.get_stock_quote("600519.SS")
            if quote_600519:
                print(f"股票: {quote_600519.get('name', 'N/A')}")
                print(f"代码: {quote_600519.get('symbol', 'N/A')}")
                print(f"价格: {quote_600519.get('price', 'N/A')}")
                print(f"涨跌幅: {quote_600519.get('changePercent', 'N/A')}%")

            # 示例2: 获取历史数据
            print("\n获取AAPL历史数据（最近30天）:")
            historical = client.get_historical_data("AAPL", "daily")
            if historical and 'data' in historical:
                data = historical['data']
                print(f"共获取 {len(data)} 条历史数据")
                if data:
                    print(f"最近一天: {data[-1]}")

            # 示例3: 趋势分析（如果服务器支持）
            print("\n尝试分析AAPL趋势:")
            trend = client.analyze_trend("AAPL", period=30)
            if trend:
                print(f"趋势分析结果: {trend.get('summary', 'N/A')}")

    finally:
        client.stop()


def integrate_with_existing_project():
    """与现有项目集成示例"""
    print("\n=== 与现有股票预测项目集成 ===\n")

    # 假设这是现有项目的股票代码列表
    stock_symbols = ["AAPL", "GOOGL", "MSFT", "600519.SS", "000001.SZ"]

    print(f"监控 {len(stock_symbols)} 只股票:\n")

    env = {}
    client = MCPStockClient(env=env)

    try:
        if not client.start():
            print("MCP服务器启动失败，使用备用数据源")
            # 这里可以添加回退到其他API的逻辑
            return

        time.sleep(2)

        for symbol in stock_symbols:
            print(f"正在获取 {symbol} 数据...")
            quote = client.get_stock_quote(symbol)

            if quote:
                price = quote.get('price', 'N/A')
                change = quote.get('changePercent', 'N/A')
                print(f"  {symbol}: 价格={price}, 涨跌幅={change}%")
            else:
                print(f"  {symbol}: 获取数据失败")

            # 避免请求过于频繁
            time.sleep(0.5)

        print("\n数据获取完成")

    finally:
        client.stop()


def enhance_stock_prediction_with_mcp():
    """使用MCP数据增强股票预测"""
    print("\n=== 使用MCP数据增强股票预测模型 ===\n")

    # 模拟现有预测流程
    print("1. 传统预测流程: 使用历史价格数据")
    print("2. 增强预测流程: 加入实时数据和技术指标")

    env = {}
    client = MCPStockClient(env=env)

    try:
        if client.start():
            time.sleep(2)

            symbol = "AAPL"

            # 获取实时数据
            print(f"\n获取 {symbol} 实时数据:")
            quote = client.get_stock_quote(symbol)
            if quote:
                print(f"  当前价格: {quote.get('price')}")
                print(f"  今日涨跌: {quote.get('changePercent')}%")

            # 获取技术指标
            print(f"\n获取 {symbol} 技术指标:")
            indicators = client.get_technical_indicators(symbol, "RSI")
            if indicators:
                print(f"  RSI指标: {indicators.get('rsi', 'N/A')}")

            # 获取新闻情感分析（需要NEWS_API_KEY）
            print(f"\n获取 {symbol} 新闻情感分析:")
            trend = client.analyze_trend(symbol, include_news=True)
            if trend and 'newsSentiment' in trend:
                sentiment = trend['newsSentiment']
                print(f"  新闻情感: {sentiment.get('sentiment', 'N/A')}")
                print(f"  置信度: {sentiment.get('confidence', 'N/A')}")

            print("\n这些数据可以用于:")
            print("  - 实时价格输入到预测模型")
            print("  - 技术指标作为特征工程")
            print("  - 新闻情感作为市场情绪指标")

    finally:
        client.stop()


if __name__ == "__main__":
    print("MCP股票分析集成示例")
    print("=" * 50)

    # 检查前置条件
    print("前置条件检查:")
    print("1. 已安装Node.js和npm: ", end="")
    try:
        # Windows兼容性检测
        result = subprocess.run("node --version", shell=True, capture_output=True, check=False, text=True)
        if result.returncode == 0:
            print("[OK]")
        else:
            print("[FAIL] (请安装Node.js)")
    except Exception:
        print("[FAIL] (请安装Node.js)")
    except FileNotFoundError:
        print("[FAIL] (请安装Node.js)")

    print("2. 可以运行npx: ", end="")
    try:
        # Windows兼容性检测
        result = subprocess.run("npx --version", shell=True, capture_output=True, check=False, text=True)
        if result.returncode == 0:
            print("[OK]")
        else:
            print("[FAIL]")
    except Exception:
        print("[FAIL]")
    except FileNotFoundError:
        print("[FAIL]")

    print("3. NEWS_API_KEY环境变量: ", end="")
    if "NEWS_API_KEY" in os.environ:
        print("[OK] (已设置)")
    else:
        print("[FAIL] (可选，用于新闻情感分析)")

    print("\n" + "=" * 50)

    # 运行示例
    try:
        example_basic_usage()
        integrate_with_existing_project()
        enhance_stock_prediction_with_mcp()

        print("\n" + "=" * 50)
        print("示例完成！")

        print("\n下一步:")
        print("1. 在您的代码中导入 mcp_stock_client 模块")
        print("2. 使用 MCPStockClient 类获取实时数据")
        print("3. 将MCP数据与现有预测模型结合")
        print("\n参考配置:")
        print("""在Claude Desktop配置中添加:
{
  "mcpServers": {
    "mcp-stock-analysis-server": {
      "command": "npx",
      "args": ["-y", "mcp-stock-analysis-server"],
      "env": {
        "NEWS_API_KEY": "your_api_key"
      }
    }
  }
}
        """)

    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n运行示例时出错: {e}")
        print("请检查:")
        print("1. Node.js和npm是否正确安装")
        print("2. 是否可以运行: npx mcp-stock-analysis-server")
        print("3. 网络连接是否正常")