import winreg
import os

def check_registry_proxy():
    """检查Windows注册表中的代理设置"""
    print("检查Windows注册表代理设置...")

    # Internet Settings路径
    paths = [
        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings\Connections",
    ]

    for path in paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
            print(f"\n检查注册表路径: HKEY_CURRENT_USER\\{path}")

            try:
                i = 0
                while True:
                    try:
                        name, value, type_ = winreg.EnumValue(key, i)
                        if 'proxy' in name.lower() or name in ['ProxyEnable', 'ProxyServer', 'ProxyOverride']:
                            print(f"  {name} = {value} (类型: {type_})")
                        i += 1
                    except OSError:
                        break
            finally:
                winreg.CloseKey(key)
        except Exception as e:
            print(f"  无法访问注册表路径: {e}")

def check_environment_proxies():
    """检查环境变量中的代理设置"""
    print("\n检查环境变量中的代理设置...")
    proxy_vars = []
    for key, value in os.environ.items():
        if 'proxy' in key.lower():
            proxy_vars.append((key, value))

    if proxy_vars:
        for key, value in proxy_vars:
            print(f"  {key} = {value}")
    else:
        print("  未找到代理相关的环境变量")

def check_winhttp_proxy():
    """检查WinHTTP代理设置"""
    print("\n检查WinHTTP代理设置...")
    try:
        import subprocess
        result = subprocess.run(['netsh', 'winhttp', 'show', 'proxy'],
                               capture_output=True, text=True, encoding='gbk')
        print(f"WinHTTP代理设置:\n{result.stdout}")
        if result.stderr:
            print(f"错误: {result.stderr}")
    except Exception as e:
        print(f"  检查WinHTTP代理失败: {e}")

if __name__ == "__main__":
    check_environment_proxies()
    try:
        check_registry_proxy()
        check_winhttp_proxy()
    except Exception as e:
        print(f"检查系统代理设置时出错: {e}")