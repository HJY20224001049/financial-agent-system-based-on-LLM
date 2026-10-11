#!/usr/bin/env python3
"""
测试 Ashare MCP 数据获取功能
"""
import asyncio
import sys
import os

# 添加当前目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_get_price():
    """测试 get_price 函数"""
    try:
        # 导入 get_price 函数
        from ashare_mcp.server import get_price

        # 测试获取上证指数最近5天的日线数据
        print("测试1: 获取上证指数最近5天的日线数据...")
        result = await get_price(
            code="sh000001",
            count=5,
            frequency="1d"
        )
        print(f"成功获取数据: {result.message}")
        print(f"数据条数: {len(result.data['records'])}")
        if result.data['records']:
            print("第一条记录:", result.data['records'][0])

        # 测试获取分钟线数据
        print("\n测试2: 获取贵州茅台最近3条15分钟线数据...")
        result2 = await get_price(
            code="sh600519",
            count=3,
            frequency="15m"
        )
        print(f"成功获取数据: {result2.message}")
        print(f"数据条数: {len(result2.data['records'])}")
        if result2.data['records']:
            print("第一条记录:", result2.data['records'][0])

        # 测试聚宽格式代码
        print("\n测试3: 使用聚宽格式代码获取数据...")
        result3 = await get_price(
            code="000001.XSHG",  # 上证指数的聚宽格式
            count=2,
            frequency="1d"
        )
        print(f"成功获取数据: {result3.message}")

        return True
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mcp_server():
    """测试MCP服务器功能"""
    try:
        # 尝试启动MCP服务器并与它通信
        print("测试MCP服务器通信...")

        # 这里可以添加通过stdio与MCP服务器通信的代码
        # 但为了简单，我们先测试直接函数调用

        return True
    except Exception as e:
        print(f"MCP服务器测试失败: {e}")
        return False

async def main():
    print("开始测试 Ashare MCP 数据获取功能...")
    print("=" * 50)

    # 测试直接函数调用
    success = await test_get_price()

    print("\n" + "=" * 50)
    if success:
        print("测试成功!")
    else:
        print("测试失败!")

    return success

if __name__ == "__main__":
    # 运行异步测试
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)