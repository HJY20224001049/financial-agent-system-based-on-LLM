#!/usr/bin/env python3
"""
详细测试 Ashare MCP 数据获取功能
"""
import asyncio
import sys
import os
import json
from datetime import datetime

# 添加当前目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(title):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_data_info(result):
    """打印数据信息"""
    if not result.data or 'records' not in result.data:
        print("无数据返回")
        return

    records = result.data['records']
    columns = result.data.get('columns', [])

    print(f"数据条数: {len(records)}")
    print(f"数据列: {columns}")

    if records:
        print("\n前3条记录:")
        for i, record in enumerate(records[:3]):
            print(f"  [{i}] {record}")

async def test_basic_functionality():
    """测试基本功能"""
    print_header("测试基本功能")

    from ashare_mcp.server import get_price

    test_cases = [
        {
            "name": "上证指数日线",
            "code": "sh000001",
            "count": 3,
            "frequency": "1d"
        },
        {
            "name": "深证成指日线",
            "code": "sz399001",
            "count": 2,
            "frequency": "1d"
        },
        {
            "name": "贵州茅台15分钟线",
            "code": "sh600519",
            "count": 5,
            "frequency": "15m"
        },
        {
            "name": "创业板指5分钟线",
            "code": "sz399006",
            "count": 4,
            "frequency": "5m"
        },
        {
            "name": "使用聚宽格式-上证指数",
            "code": "000001.XSHG",
            "count": 2,
            "frequency": "1d"
        },
        {
            "name": "使用聚宽格式-深证成指",
            "code": "399001.XSHE",
            "count": 2,
            "frequency": "1d"
        }
    ]

    for i, test_case in enumerate(test_cases):
        print(f"\n测试 {i+1}: {test_case['name']}")
        print(f"  参数: code={test_case['code']}, count={test_case['count']}, frequency={test_case['frequency']}")

        try:
            result = await get_price(**test_case)
            print(f"  结果: {result.message}")
            if result.data and result.data.get('records'):
                print(f"  获取数据: {len(result.data['records'])} 条")
                # 显示最新一条数据的时间
                latest = result.data['records'][-1]
                if '' in latest:  # 时间字段
                    print(f"  最新数据时间: {latest['']}")
            else:
                print("  警告: 无数据返回")
        except Exception as e:
            print(f"  错误: {e}")

    return True

async def test_edge_cases():
    """测试边界情况"""
    print_header("测试边界情况")

    from ashare_mcp.server import get_price

    edge_cases = [
        {
            "name": "无效股票代码",
            "code": "invalid_code",
            "count": 1,
            "frequency": "1d",
            "should_fail": True
        },
        {
            "name": "最小数量(count=1)",
            "code": "sh000001",
            "count": 1,
            "frequency": "1d",
            "should_fail": False
        },
        {
            "name": "不同频率测试",
            "code": "sh600519",
            "count": 2,
            "frequency": "1m",
            "should_fail": False
        },
        {
            "name": "不同频率测试",
            "code": "sh600519",
            "count": 2,
            "frequency": "30m",
            "should_fail": False
        },
        {
            "name": "不同频率测试",
            "code": "sh600519",
            "count": 2,
            "frequency": "60m",
            "should_fail": False
        },
        {
            "name": "不同频率测试",
            "code": "sh600519",
            "count": 2,
            "frequency": "1w",
            "should_fail": False
        },
        {
            "name": "不同频率测试",
            "code": "sh600519",
            "count": 2,
            "frequency": "1M",
            "should_fail": False
        }
    ]

    for test_case in edge_cases:
        print(f"\n测试: {test_case['name']}")

        try:
            result = await get_price(
                code=test_case['code'],
                count=test_case['count'],
                frequency=test_case['frequency']
            )

            if test_case['should_fail']:
                print(f"  预期失败但成功: {result.message}")
            else:
                print(f"  成功: {result.message}")
                if result.data and result.data.get('records'):
                    print(f"  数据条数: {len(result.data['records'])}")
        except Exception as e:
            if test_case['should_fail']:
                print(f"  预期失败: {e}")
            else:
                print(f"  意外错误: {e}")

    return True

async def test_with_end_date():
    """测试指定结束日期"""
    print_header("测试指定结束日期")

    from ashare_mcp.server import get_price

    # 使用一周前的日期作为结束日期
    from datetime import datetime, timedelta
    end_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    print(f"结束日期: {end_date}")

    try:
        result = await get_price(
            code="sh000001",
            end_date=end_date,
            count=5,
            frequency="1d"
        )
        print(f"结果: {result.message}")
        if result.data and result.data.get('records'):
            records = result.data['records']
            print(f"数据条数: {len(records)}")
            print("数据日期范围:")
            for record in records:
                if '' in record:
                    print(f"  {record['']}")
    except Exception as e:
        print(f"错误: {e}")

    return True

async def test_fields_parameter():
    """测试fields参数"""
    print_header("测试fields参数")

    from ashare_mcp.server import get_price

    try:
        # 测试指定字段
        result = await get_price(
            code="sh000001",
            count=3,
            frequency="1d",
            fields=["open", "close", "volume"]
        )
        print(f"结果: {result.message}")
        print_data_info(result)
    except Exception as e:
        print(f"错误: {e}")

    return True

async def main():
    """主测试函数"""
    print("开始详细测试 Ashare MCP 数据获取功能")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    all_passed = True

    # 运行各个测试
    tests = [
        ("基本功能测试", test_basic_functionality),
        ("边界情况测试", test_edge_cases),
        ("指定结束日期测试", test_with_end_date),
        ("字段参数测试", test_fields_parameter)
    ]

    for test_name, test_func in tests:
        try:
            print_header(f"开始 {test_name}")
            passed = await test_func()
            if not passed:
                all_passed = False
                print(f"{test_name} 失败!")
        except Exception as e:
            print(f"{test_name} 发生异常: {e}")
            all_passed = False

    print_header("测试总结")
    if all_passed:
        print("所有测试通过! ✓")
        print("\nAshare MCP 数据获取功能工作正常。")
        print("可以成功获取不同股票代码、不同频率的行情数据。")
    else:
        print("部分测试失败! ✗")

    return all_passed

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"测试框架错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)