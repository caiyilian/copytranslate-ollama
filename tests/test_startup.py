"""Startup 模块单元测试。"""

import sys

from core.startup import (
    _get_exe_path,
    is_enabled,
    enable,
    disable,
    toggle,
)


class TestStartup:
    """测试开机自启管理函数。"""

    def test_get_exe_path_returns_string(self) -> None:
        """_get_exe_path 应返回路径字符串或 None。"""
        path = _get_exe_path()
        # Windows 上应返回路径，其他平台返回 None
        if sys.platform == "win32":
            assert path is not None
            assert isinstance(path, str)
            assert len(path) > 0
        else:
            assert path is None

    def test_is_enabled_no_error(self) -> None:
        """is_enabled 不抛出异常。"""
        try:
            result = is_enabled()
            assert isinstance(result, bool)
        except Exception as e:
            assert False, f"is_enabled() raised {e}"

    def test_disable_no_error(self) -> None:
        """disable 不抛出异常。"""
        try:
            result = disable()
            assert isinstance(result, bool)
        except Exception as e:
            assert False, f"disable() raised {e}"

    def test_enable_no_error(self) -> None:
        """enable 不抛出异常。"""
        try:
            result = enable()
            assert isinstance(result, bool)
        except Exception as e:
            assert False, f"enable() raised {e}"

    def test_toggle_no_error(self) -> None:
        """toggle 不抛出异常。"""
        try:
            result = toggle()
            assert isinstance(result, bool)
        except Exception as e:
            assert False, f"toggle() raised {e}"