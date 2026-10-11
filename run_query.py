#!/usr/bin/env python3
"""
运行查询的Python脚本
替代 run_app.bat 中的查询逻辑
直接调用 ashare_mcp 模块，避免子进程问题
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# 清除所有代理环境变量，防止网络连接失败
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
# 设置requests库不使用代理
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['CURL_CA_BUNDLE'] = ''
# 可选：禁用HTTPS验证（仅用于测试环境）
os.environ['PYTHONHTTPSVERIFY'] = '0'

# 添加Ashare-mcp目录到Python路径
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

def plot_stock_data(result, stock_code, output_file=None):
    """绘制股票数据折线图

    Args:
        result: get_price返回的结果对象，包含data字段
        stock_code: 股票代码（用于标题）
        output_file: 输出文件路径，如果为None则自动生成
    """
    try:
        # 检查matplotlib是否可用
        import matplotlib.pyplot as plt
        import matplotlib
    except ImportError:
        print("警告: matplotlib未安装，无法绘制图表。请安装: pip install matplotlib")
        return

    if not hasattr(result, 'data'):
        print("错误: 结果对象缺少data字段")
        return

    data = result.data
    if not isinstance(data, dict):
        print("错误: data字段不是字典类型")
        return

    records = data.get('records', [])
    columns = data.get('columns', [])

    if not records:
        print("错误: 数据为空，无法绘制图表")
        return

    # 检查records的数据类型：字典列表还是列表的列表
    first_record = records[0]
    is_dict_records = isinstance(first_record, dict)

    # 如果columns为空但records是字典列表，可以从字典键中推断列名
    if not columns and is_dict_records:
        # 使用第一个字典的所有键作为列名（除了可能的空键）
        columns = [key for key in first_record.keys() if key != '']

    if not columns:
        print("警告: 无法确定列名，尝试使用默认列名")
        columns = []

    # 查找日期/时间和价格列名或索引
    date_key = None
    close_key = None
    open_key = None
    high_key = None
    low_key = None

    for col in columns:
        col_str = str(col)
        col_lower = col_str.lower()
        if 'date' in col_lower or '时间' in col_lower or 'datetime' in col_lower:
            date_key = col_str
        elif 'close' in col_lower or '收盘' in col_lower:
            close_key = col_str
        elif 'open' in col_lower or '开盘' in col_lower:
            open_key = col_str
        elif 'high' in col_lower or '最高' in col_lower:
            high_key = col_str
        elif 'low' in col_lower or '最低' in col_lower:
            low_key = col_str

    # 如果未找到列名，但records是字典列表，尝试从字典键中查找
    if is_dict_records:
        for key in first_record.keys():
            if key == '':
                continue
            key_lower = str(key).lower()
            if 'date' in key_lower or '时间' in key_lower or 'datetime' in key_lower:
                date_key = key
            elif 'close' in key_lower or '收盘' in key_lower:
                close_key = key
            elif 'open' in key_lower or '开盘' in key_lower:
                open_key = key
            elif 'high' in key_lower or '最高' in key_lower:
                high_key = key
            elif 'low' in key_lower or '最低' in key_lower:
                low_key = key

    # 如果仍未找到日期列，使用索引作为X轴
    if date_key is None:
        print("警告: 未找到日期列，使用索引作为X轴")
        dates = list(range(len(records)))
    else:
        dates = []
        for record in records:
            if is_dict_records:
                date_val = record.get(date_key) if isinstance(record, dict) else None
            else:
                # 列表的列表，需要找到date_key在columns中的索引
                try:
                    col_idx = columns.index(date_key)
                    date_val = record[col_idx] if col_idx < len(record) else None
                except ValueError:
                    date_val = None

            if date_val is None:
                dates.append('')
                continue

            date_str = str(date_val)
            # 尝试解析日期字符串
            try:
                # 尝试常见格式
                if ' ' in date_str:
                    dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                elif 'T' in date_str:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                dates.append(dt)
            except ValueError:
                # 如果解析失败，使用原始字符串
                dates.append(date_str)

    if close_key is None:
        print("错误: 未找到收盘价列，无法绘制图表")
        return

    # 提取收盘价数据
    close_prices = []
    for record in records:
        price = None
        if is_dict_records:
            price = record.get(close_key) if isinstance(record, dict) else None
        else:
            try:
                col_idx = columns.index(close_key)
                price = record[col_idx] if col_idx < len(record) else None
            except ValueError:
                price = None

        if price is None:
            close_prices.append(0.0)
            continue

        try:
            close_prices.append(float(price))
        except (ValueError, TypeError):
            close_prices.append(0.0)

    # 创建图表
    plt.figure(figsize=(12, 6))

    # 绘制收盘价折线
    plt.plot(dates, close_prices, label='收盘价', linewidth=2, color='blue', marker='o', markersize=4)

    # 可选：绘制开盘价、最高价、最低价（如果存在）
    if open_key is not None:
        open_prices = []
        for record in records:
            price = None
            if is_dict_records:
                price = record.get(open_key) if isinstance(record, dict) else None
            else:
                try:
                    col_idx = columns.index(open_key)
                    price = record[col_idx] if col_idx < len(record) else None
                except ValueError:
                    price = None

            if price is None:
                open_prices.append(0.0)
                continue

            try:
                open_prices.append(float(price))
            except (ValueError, TypeError):
                open_prices.append(0.0)
        plt.plot(dates, open_prices, label='开盘价', linewidth=1, color='green', linestyle='--', marker='^', markersize=3)

    if high_key is not None:
        high_prices = []
        for record in records:
            price = None
            if is_dict_records:
                price = record.get(high_key) if isinstance(record, dict) else None
            else:
                try:
                    col_idx = columns.index(high_key)
                    price = record[col_idx] if col_idx < len(record) else None
                except ValueError:
                    price = None

            if price is None:
                high_prices.append(0.0)
                continue

            try:
                high_prices.append(float(price))
            except (ValueError, TypeError):
                high_prices.append(0.0)
        plt.plot(dates, high_prices, label='最高价', linewidth=1, color='red', linestyle=':', marker='v', markersize=3)

    if low_key is not None:
        low_prices = []
        for record in records:
            price = None
            if is_dict_records:
                price = record.get(low_key) if isinstance(record, dict) else None
            else:
                try:
                    col_idx = columns.index(low_key)
                    price = record[col_idx] if col_idx < len(record) else None
                except ValueError:
                    price = None

            if price is None:
                low_prices.append(0.0)
                continue

            try:
                low_prices.append(float(price))
            except (ValueError, TypeError):
                low_prices.append(0.0)
        plt.plot(dates, low_prices, label='最低价', linewidth=1, color='orange', linestyle='-.', marker='s', markersize=3)

    plt.title(f'{stock_code} 股票价格走势 (收盘价)')
    plt.xlabel('日期')
    plt.ylabel('价格')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)

    # 自动旋转X轴日期标签
    if len(dates) > 5 and all(isinstance(d, datetime) for d in dates):
        plt.gcf().autofmt_xdate()

    # 保存图表
    if output_file is None:
        # 生成默认文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'{stock_code}_{timestamp}_price_chart.png'

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"图表已保存: {output_file}")
    plt.close()


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: run_query.py query <股票代码> [选项]")
        print("选项:")
        print("  --count <N>        K线数量，默认10")
        print("  --frequency <F>    K线周期，默认1d")
        print("  --end-date <DATE>  结束日期，格式YYYY-MM-DD")
        print("  --plot             绘制价格折线图")
        print("  --output <FILE>    图表输出文件路径（默认自动生成）")
        sys.exit(1)

    if sys.argv[1] != "query":
        print(f"错误: 未知命令 {sys.argv[1]}")
        print("用法: run_query.py query <股票代码> [选项]")
        sys.exit(1)

    if len(sys.argv) < 3:
        print("错误: 查询模式需要指定股票代码。")
        sys.exit(1)

    # 解析参数
    stock_code = sys.argv[2]
    count = 10
    frequency = "1d"
    end_date = ""
    plot = False
    output_file = None

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--count" and i + 1 < len(sys.argv):
            count = int(sys.argv[i + 1])
            i += 2
        elif arg == "--frequency" and i + 1 < len(sys.argv):
            frequency = sys.argv[i + 1]
            i += 2
        elif arg == "--end-date" and i + 1 < len(sys.argv):
            end_date = sys.argv[i + 1]
            i += 2
        elif arg == "--plot":
            plot = True
            i += 1
        elif arg == "--output" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        else:
            print(f"警告: 忽略未知参数 {arg}")
            i += 1

    # 获取数据
    print(f"查询: {stock_code} count={count} frequency={frequency}")
    try:
        result = asyncio.run(get_stock_data(
            code=stock_code,
            count=count,
            frequency=frequency,
            end_date=end_date
        ))
    except RuntimeError as e:
        # 如果已有事件循环（如在Jupyter或某些环境中），使用不同方法
        try:
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(get_stock_data(
                code=stock_code,
                count=count,
                frequency=frequency,
                end_date=end_date
            ))
        except ImportError:
            print("需要nest_asyncio来处理现有事件循环", file=sys.stderr)
            sys.exit(1)

    if result is None:
        print("获取数据失败", file=sys.stderr)
        sys.exit(1)

    # 绘图功能
    if plot:
        plot_stock_data(result, stock_code, output_file)

    # 输出结果
    output = {
        'code': result.code,
        'message': result.message,
        'data': result.data
    }
    print(json.dumps(output, indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()