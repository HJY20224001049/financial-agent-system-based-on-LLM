"""
MCP股票分析快速开始
最简单的入门示例
"""

import os
import sys
import subprocess
import json
import platform

def check_prerequisites():
    """检查前置条件"""
    print("检查前置条件...")

    # 根据平台确定可执行文件名
    is_windows = platform.system() == "Windows"
    node_cmd = "node"
    npx_cmd = "npx.cmd" if is_windows else "npx"
    npm_cmd = "npm.cmd" if is_windows else "npm"

    # 检查Node.js
    try:
        result = subprocess.run(f"{node_cmd} --version", shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"[OK] Node.js 已安装: {result.stdout.strip()}")
        else:
            print("[FAIL] Node.js 未安装或不可用")
            return False
    except FileNotFoundError:
        print("[FAIL] Node.js 未安装，请从 https://nodejs.org/ 下载安装")
        return False

    # 检查npm/npx
    # 先尝试npx，如果失败再尝试npm
    try:
        result = subprocess.run(f"{npx_cmd} --version", shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"[OK] npx 可用: {result.stdout.strip()}")
            return True
        else:
            print(f"[WARN] npx 检查失败 (返回值 {result.returncode})，尝试npm...")
    except FileNotFoundError:
        print("[WARN] npx 未找到，尝试npm...")

    # 尝试npm作为后备
    try:
        result = subprocess.run(f"{npm_cmd} --version", shell=True, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            print(f"[OK] npm 可用: {result.stdout.strip()}")
            print("[INFO] npx 可能因PowerShell执行策略被阻止，但npm可用")
            print("[INFO] 要解决此问题，可以:")
            print("       1. 以管理员身份运行: Set-ExecutionPolicy RemoteSigned -Scope CurrentUser")
            print("       2. 或使用CMD命令提示符而非PowerShell")
            print("       3. 或直接使用 npm install -g mcp-stock-analysis-server")
            return True
        else:
            print("[FAIL] npm 也不可用")
            return False
    except FileNotFoundError:
        print("[FAIL] npm 不可用，请确保npm已正确安装")
        return False

def install_mcp_server():
    """安装MCP服务器"""
    print("\n安装 mcp-stock-analysis-server...")

    # 根据平台确定可执行文件名
    is_windows = platform.system() == "Windows"
    npx_cmd = "npx.cmd" if is_windows else "npx"
    npm_cmd = "npm.cmd" if is_windows else "npm"

    try:
        # 使用npx运行，不需要全局安装
        print(f"正在测试 {npx_cmd} mcp-stock-analysis-server --help...")
        result = subprocess.run(
            f"{npx_cmd} -y mcp-stock-analysis-server --help",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )

        if result.returncode == 0:
            print("[OK] MCP服务器可用")
            return True
        else:
            # 安全地获取错误信息
            stderr_output = result.stderr if result.stderr else result.stdout if result.stdout else "无错误信息"
            # 限制长度
            error_preview = stderr_output[:500] if stderr_output else "无错误信息"
            print(f"[FAIL] MCP服务器测试失败 (返回码 {result.returncode}): {error_preview}")
            # 尝试使用npm全局安装的版本
            print("尝试使用npm全局安装的版本...")
            return False

    except FileNotFoundError:
        print(f"[WARN] {npx_cmd} 未找到，尝试使用npm...")
        # 尝试使用npm run？需要全局安装
        print("请确保已全局安装 mcp-stock-analysis-server: npm install -g mcp-stock-analysis-server")
        return False
    except subprocess.TimeoutExpired:
        print("[OK] MCP服务器启动测试超时（可能是正常的）")
        return True
    except Exception as e:
        print(f"[FAIL] 测试MCP服务器时出错: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def simple_example():
    """最简单的使用示例"""
    print("\n" + "="*50)
    print("最简单的使用示例")
    print("="*50)

    # 方法1: 直接使用npx命令（最简单）
    print("\n方法1: 直接使用npx命令获取数据")
    print("="*30)

    # 注意：MCP服务器通常通过stdio通信，不能直接通过命令行参数获取数据
    # 这里展示一个概念性示例

    print("""由于MCP服务器使用JSON-RPC over stdio协议，需要专门的客户端。
我们已经创建了 mcp_stock_client.py，提供了完整的客户端实现。

最简单的使用方式:
""")

    code = """
# 最简单的使用示例
from mcp_stock_client import quick_start

# 获取AAPL股票报价
quote = quick_start("AAPL")
if quote:
    print(f"股票报价: {quote}")
"""

    print(code)

    print("\n" + "="*50)
    print("快速测试")
    print("="*50)

    # 尝试导入并运行快速测试
    try:
        from mcp_stock_client import quick_start

        print("正在测试 quick_start('AAPL')...")
        print("注意: 这会启动MCP服务器进程，可能需要几秒钟")

        quote = quick_start("AAPL")
        if quote:
            print(f"[OK] 测试成功！获取到数据: {json.dumps(quote, indent=2, ensure_ascii=False)}")
        else:
            print("[FAIL] 测试失败，但服务器可能已启动")

    except ImportError as e:
        print(f"[FAIL] 导入失败: {e}")
        print("请确保 mcp_stock_client.py 在同一目录下")
    except Exception as e:
        print(f"[FAIL] 测试过程中出错: {e}")

def configuration_guide():
    """配置指南"""
    print("\n" + "="*50)
    print("配置指南")
    print("="*50)

    print("""
1. Claude Desktop 配置 (推荐)
--------------------------------
在Claude Desktop的配置文件中添加:

{
  "mcpServers": {
    "mcp-stock-analysis-server": {
      "command": "npx",
      "args": ["-y", "mcp-stock-analysis-server"],
      "env": {
        "NEWS_API_KEY": "your_news_api_key_here"
      }
    }
  }
}

配置后，Claude Desktop会自动启动MCP服务器，并通过MCP协议与AI助手通信。

2. Python项目集成
--------------------------------
在Python代码中使用我们的客户端:

from mcp_stock_client import MCPStockClient

# 创建客户端（可设置环境变量）
client = MCPStockClient(env={"NEWS_API_KEY": "your_key"})

# 启动服务器
client.start()

# 获取数据
quote = client.get_stock_quote("AAPL")
historical = client.get_historical_data("AAPL", "daily")

# 停止服务器
client.stop()

3. 环境变量
--------------------------------
- NEWS_API_KEY: 用于新闻情感分析（可选）
  注册地址: https://newsapi.org/

4. 常见股票代码格式
--------------------------------
- 美股: AAPL, GOOGL, MSFT
- A股: 600519.SS (上证), 000001.SZ (深证)
- 港股: 0700.HK
- 指数: ^GSPC (标普500), ^IXIC (纳斯达克)
""")

def main():
    print("MCP股票分析快速开始")
    print("="*50)

    # 检查前置条件
    if not check_prerequisites():
        print("\n请先安装必要的依赖:")
        print("1. 安装Node.js: https://nodejs.org/")
        print("2. 确保npm/npx可用")
        return

    # 测试MCP服务器
    if not install_mcp_server():
        print("\nMCP服务器可能无法直接访问，但客户端可能仍能工作")
        print("您可以尝试手动安装: npm install -g mcp-stock-analysis-server")

    # 显示简单示例
    simple_example()

    # 配置指南
    configuration_guide()

    print("\n" + "="*50)
    print("快速开始完成!")
    print("="*50)
    print("\n下一步:")
    print("1. 查看 use_mcp_example.py 了解更多使用示例")
    print("2. 查看 mcp_stock_client.py 了解客户端实现细节")
    print("3. 在您的项目中导入并使用 MCPStockClient 类")
    print("\n更多资源:")
    print("- MCP服务器主页: https://www.scnet.cn/ui/aihub/mcp/renchang1016/stock-mcp")
    print("- News API: https://newsapi.org/")
    print("- Yahoo Finance: https://finance.yahoo.com/")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()