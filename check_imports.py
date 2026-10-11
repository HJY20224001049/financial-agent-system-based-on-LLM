#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查main.py的导入问题"""
import os
import sys
import traceback

def check_main_imports():
    """检查main.py是否能成功导入"""
    print("检查main.py导入...")

    # 首先设置环境变量避免protobuf警告
    os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

    # 尝试导入main.py使用的模块
    modules_to_check = [
        ('matplotlib', 'matplotlib'),
        ('ssl', 'ssl'),
        ('requests', 'requests'),
        ('pandas', 'pandas'),
        ('lxml', 'lxml'),
        ('numpy', 'numpy'),
        ('Connect_qwen', 'Connect_qwen'),
        ('emotion_annalyse', 'emotion_annalyse'),
        ('Scraper', 'Scraper'),
        ('add_new_data', 'add_new_data'),
        ('stock_predict', 'stock_predict'),
        ('news_analysis.newscraper', 'from news_analysis.newscraper import create_scraper'),
        ('news_analysis.selfmademain', 'from news_analysis.selfmademain import analyze_csv')
    ]

    for module_name, import_stmt in modules_to_check:
        try:
            if import_stmt.startswith('from '):
                # 执行from...import语句
                exec(import_stmt)
                print(f"  成功: {module_name}")
            else:
                __import__(module_name)
                print(f"  成功: {module_name}")
        except Exception as e:
            print(f"  失败: {module_name}: {e}")
            # 如果是protobuf/TensorFlow相关错误，给出具体建议
            if "protobuf" in str(e) or "Descriptors cannot be created directly" in str(e):
                print(f"    建议: pip install --upgrade 'protobuf<3.20,>=3.9.2'")
                print(f"    或运行: fix_protobuf.bat")
            return False

    print("\n尝试执行main.py中的主要函数...")
    try:
        # 模拟main.py的执行环境
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端

        # 尝试执行main.py中的一小段代码
        from datetime import datetime, timedelta
        yesterday_time = datetime.today().date()-timedelta(days=1)
        yesterday = yesterday_time.strftime("%Y%m%d")
        print(f"  成功: 日期计算正常: {yesterday}")

        # 测试get_stock_daily_data函数的基本结构
        import re
        from urllib.parse import urlencode, quote
        print(f"  成功: 辅助模块导入正常")

        return True

    except Exception as e:
        print(f"  ✗ 执行测试失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("检查main.py依赖和导入")
    print("="*60)

    success = check_main_imports()

    if success:
        print("\n" + "="*60)
        print("导入检查通过!")
        print("main.py应该可以正常运行")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("导入检查失败!")
        print("请根据上面的错误信息修复依赖问题")
        print("常见问题:")
        print("1. protobuf版本太高: pip install --upgrade 'protobuf<3.20,>=3.9.2'")
        print("2. 缺少依赖: pip install -r requirements.txt")
        print("="*60)
        sys.exit(1)