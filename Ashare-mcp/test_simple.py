#!/usr/bin/env python3
"""
简单测试 Ashare MCP 数据获取功能
"""
import asyncio
import sys
import os

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# 添加当前目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_basic():
    """测试基本功能"""
    from ashare_mcp.server import get_price

    print("测试 Ashare MCP 数据获取功能")
    print("=" * 50)

    # 测试1: 上证指数日线
    print("\n1. 测试上证指数日线数据:")
    result = await get_price(code="sh000001", count=3, frequency="1d")
    print(f"   结果: {result.message}")
    if result.data and result.data.get('records'):
        print(f"   数据条数: {len(result.data['records'])}")
        for i, rec in enumerate(result.data['records']):
            print(f"   第{i+1}条: 时间={rec.get('')}, 开盘={rec.get('open')}, 收盘={rec.get('close')}")

    # 测试2: 分钟线数据
    print("\n2. 测试分钟线数据:")
    result = await get_price(code="sh600519", count=2, frequency="15m")
    print(f"   结果: {result.message}")
    if result.data and result.data.get('records'):
        print(f"   数据条数: {len(result.data['records'])}")

    # 测试3: 聚宽格式
    print("\n3. 测试聚宽格式代码:")
    result = await get_price(code="000001.XSHG", count=1, frequency="1d")
    print(f"   结果: {result.message}")

    # 测试4: 不同频率
    print("\n4. 测试不同频率:")
    frequencies = ['5m', '30m', '60m', '1w', '1M']
    for freq in frequencies:
        try:
            result = await get_price(code="sh600519", count=1, frequency=freq)
            print(f"   {freq}: {result.message}")
        except Exception as e:
            print(f"   {freq}: 失败 - {e}")

    return True

async def main():
    try:
        success = await test_basic()
        print("\n" + "=" * 50)
        print("测试完成!" if success else "测试失败!")
        return success
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # 在Windows上设置控制台编码
    if sys.platform == "win32":
        os.system("chcp 65001 > nul")

    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n测试中断")
        sys.exit(1)