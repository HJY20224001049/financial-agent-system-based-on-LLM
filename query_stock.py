#!/usr/bin/env python3
"""
股票数据查询脚本
直接调用 ashare_mcp 模块获取股票数据
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# 添加Ashare-mcp目录到Python路径
# 从当前目录 (pythonProject/pythonProject) 向上两级到毕业设计目录
current_dir = os.path.dirname(__file__)
ashare_mcp_dir = os.path.join(current_dir, "..", "..", "Ashare-mcp")
ashare_mcp_dir = os.path.abspath(ashare_mcp_dir)
if ashare_mcp_dir not in sys.path:
    sys.path.insert(0, ashare_mcp_dir)

async def get_stock_data(code, count=10, frequency='1d', end_date=''):
    """获取股票数据"""
    try:
        from ashare_mcp.server import get_price

        result = await get_price(
            code=code,
            end_date=end_date,
            count=count,
            frequency=frequency
        )

        return result
    except ImportError as e:
        print(f"导入ashare_mcp模块失败: {e}", file=sys.stderr)
        print("请确保Ashare-mcp目录在项目根目录下", file=sys.stderr)
        return None
    except Exception as e:
        print(f"获取股票数据失败: {e}", file=sys.stderr)
        return None

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="查询股票数据")
    parser.add_argument("code", help="股票代码，如 sh000001 或 600519")
    parser.add_argument("--count", type=int, default=10, help="K线数量，默认10")
    parser.add_argument("--frequency", default="1d",
                       choices=['1m', '5m', '15m', '30m', '60m', '1d', '1w', '1M'],
                       help="K线周期，默认1d")
    parser.add_argument("--end-date", default="", help="结束日期，格式 YYYY-MM-DD")
    parser.add_argument("--format", choices=['json', 'table', 'csv'], default='json',
                       help="输出格式，默认json")

    args = parser.parse_args()

    # 运行异步函数
    try:
        result = asyncio.run(get_stock_data(
            code=args.code,
            count=args.count,
            frequency=args.frequency,
            end_date=args.end_date
        ))
    except RuntimeError as e:
        # 如果已有事件循环（如在Jupyter或某些环境中），使用不同方法
        import nest_asyncio
        nest_asyncio.apply()
        result = asyncio.run(get_stock_data(
            code=args.code,
            count=args.count,
            frequency=args.frequency,
            end_date=args.end_date
        ))

    if result is None:
        sys.exit(1)

    # 输出结果
    if args.format == 'json':
        # 转换为可序列化的字典
        output = {
            'code': result.code,
            'message': result.message,
            'data': result.data
        }
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    elif args.format == 'table':
        if result.data and 'records' in result.data:
            records = result.data['records']
            if records:
                print(f"股票代码: {result.code}")
                print(f"消息: {result.message}")
                print(f"数据条数: {len(records)}")
                print("\n数据详情:")
                # 打印表头
                headers = list(records[0].keys())
                print(" | ".join(headers))
                print("-" * 50)
                for rec in records:
                    row = [str(rec.get(h, '')) for h in headers]
                    print(" | ".join(row))
        else:
            print(f"股票代码: {result.code}")
            print(f"消息: {result.message}")
            print("无数据记录")
    elif args.format == 'csv':
        if result.data and 'records' in result.data:
            records = result.data['records']
            if records:
                headers = list(records[0].keys())
                print(",".join(headers))
                for rec in records:
                    row = [str(rec.get(h, '')) for h in headers]
                    print(",".join(row))
        else:
            print("无数据记录")

if __name__ == "__main__":
    main()