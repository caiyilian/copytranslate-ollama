"""开机自启管理器（Windows 注册表方式）。

通过 HKCU\Software\Microsoft\Windows\CurrentVersion\Run 注册表项
实现当前用户的开机自启。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

# 仅在 Windows 上导入 winreg
if sys.platform == "win32":
    import winreg


# 注册表路径和值名称
_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_VALUE = "CopyTranslatorOllama"


def _get_exe_path() -> Optional[str]:
    """获取启动时运行的可执行文件路径。

    优先使用 pythonw.exe（无控制台窗口），
    回退到 python.exe。
    """
    # 如果打包成了 exe，使用 sys.executable
    exe = Path(sys.executable)
    if exe.name.lower() in ("python.exe", "pythonw.exe"):
        # 开发模式：使用 pythonw.exe 运行 main.py
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            # 找项目根目录的 main.py
            script = Path(__file__).resolve().parent.parent / "main.py"
            if script.exists():
                return f'"{pythonw}" "{script}"'
        # 回退到 python.exe
        if exe.exists():
            script = Path(__file__).resolve().parent.parent / "main.py"
            if script.exists():
                return f'"{exe}" "{script}"'
    else:
        # 打包后的 exe
        return str(exe)
    return None


def is_enabled() -> bool:
    """检查开机自启是否已启用。"""
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, _REG_VALUE)
            return bool(value)
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    """启用开机自启。

    Returns:
        True 如果成功。
    """
    if sys.platform != "win32":
        return False
    exe_path = _get_exe_path()
    if not exe_path:
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.SetValueEx(
                key, _REG_VALUE, 0, winreg.REG_SZ, exe_path
            )
            return True
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def disable() -> bool:
    """禁用开机自启。

    Returns:
        True 如果成功。
    """
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, _REG_VALUE)
            return True
        except FileNotFoundError:
            return True  # 已经不存在也算成功
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def toggle() -> bool:
    """切换开机自启状态。

    Returns:
        切换后的状态（True=启用）。
    """
    if is_enabled():
        disable()
        return False
    else:
        enable()
        return True