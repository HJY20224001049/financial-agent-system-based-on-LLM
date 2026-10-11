#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试main.py是否能正常运行"""
import subprocess
import sys
import os

def test_main_py():
    """测试main.py的基本功能"""
    print("测试main.py...")

    # 尝试运行main.py，发送一个简单的输入
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # 重定向stderr到stdout
        text=True,
        encoding='utf-8',
        cwd=os.getcwd()
    )

    try:
        # 发送一个简单的问题
        test_question = "分析贵州茅台\n"
        stdout, _ = process.communicate(input=test_question, timeout=30)
        return_code = process.returncode

        print(f"返回码: {return_code}")
        print(f"输出前500字符:")
        print(stdout[:500] if stdout else "无输出")

        if return_code != 0:
            print(f"main.py异常退出，返回码: {return_code}")
            return False
        else:
            print("main.py运行成功")
            return True

    except subprocess.TimeoutExpired:
        print("测试超时")
        process.kill()
        return False
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """测试必要的依赖是否安装"""
    print("测试依赖...")
    imports = [
        "matplotlib",
        "ssl",
        "requests",
        "pandas",
        "lxml",
        "numpy",
        "Connect_qwen",
        "emotion_annalyse",
        "Scraper",
        "add_new_data",
        "stock_predict"
    ]

    for imp in imports:
        try:
            if imp == "Connect_qwen":
                __import__("Connect_qwen")
            elif imp == "emotion_annalyse":
                __import__("emotion_annalyse")
            elif imp == "Scraper":
                __import__("Scraper")
            elif imp == "add_new_data":
                __import__("add_new_data")
            elif imp == "stock_predict":
                __import__("stock_predict")
            else:
                __import__(imp)
            print(f"  成功: {imp}")
        except ImportError as e:
            print(f"  ✗ {imp}: {e}")
            return False

    return True

if __name__ == "__main__":
    print("="*60)
    print("股票分析系统测试")
    print("="*60)

    deps_ok = test_dependencies()
    if not deps_ok:
        print("\n部分依赖未安装，请运行: pip install -r requirements.txt")
        sys.exit(1)

    print("\n" + "="*60)
    print("测试main.py执行...")
    print("="*60)

    success = test_main_py()

    if success:
        print("\n测试通过!")
    else:
        print("\n测试失败!")
        sys.exit(1)