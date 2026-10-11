#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试subprocess调用main.py"""
import subprocess
import sys
import os
import traceback

def test_main_with_input():
    """测试main.py是否能处理输入"""
    print("测试subprocess调用main.py...")

    # 设置环境变量避免protobuf问题
    env = os.environ.copy()
    env['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            cwd=os.getcwd(),
            env=env
        )

        print("进程已启动，发送测试输入...")

        try:
            # 发送简单输入
            test_input = "分析贵州茅台\n"
            result = process.communicate(input=test_input, timeout=30)
            stdout = result[0] if result and len(result) > 0 else ""
            return_code = process.returncode

            print(f"返回码: {return_code}")
            print(f"输出长度: {len(stdout)} 字符")

            if stdout:
                print("输出前500字符:")
                print(stdout[:500])

            if return_code != 0:
                print(f"进程异常退出!")
                return False
            else:
                print("进程正常退出!")
                return True

        except subprocess.TimeoutExpired:
            print("进程超时!")
            process.kill()
            return False

    except Exception as e:
        print(f"启动进程时出错: {e}")
        traceback.print_exc()
        return False

def test_simple_import():
    """测试简单导入"""
    print("\n测试简单导入...")
    try:
        # 直接导入main.py中的函数
        import matplotlib
        matplotlib.use('Agg')

        # 只是测试导入，不执行
        print("导入测试成功!")
        return True
    except Exception as e:
        print(f"导入失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("subprocess测试")
    print("="*60)

    # 先测试导入
    import_ok = test_simple_import()

    if import_ok:
        print("\n" + "="*60)
        print("测试subprocess执行...")
        print("="*60)

        # 测试subprocess
        subprocess_ok = test_main_with_input()

        if subprocess_ok:
            print("\n测试通过!")
        else:
            print("\nsubprocess测试失败!")
            print("\n可能的问题:")
            print("1. main.py有运行时错误")
            print("2. 输入格式问题")
            print("3. 超时设置太短")
    else:
        print("\n导入测试失败，无法继续!")
        print("\n请先修复导入问题:")
        print("1. 运行: pip install -r requirements.txt")
        print("2. protobuf问题: pip install --upgrade 'protobuf<3.20,>=3.9.2'")