"""SystemTray 功能测试。"""

from ui.tray import SystemTray


class TestSystemTray:
    def test_tray_import(self) -> None:
        """验证 SystemTray 模块可导入。"""
        assert SystemTray is not None

    def test_tray_instantiate(self) -> None:
        """验证 SystemTray 可实例化。"""
        tray = SystemTray(
            tooltip="TestTray",
            on_show=lambda: None,
            on_quit=lambda: None,
        )
        assert tray is not None
        assert tray._tooltip == "TestTray"