"""Toast 通知组件单元测试。"""

from ui.toast import Toast, _TOAST_COLORS


class TestToast:
    """测试 Toast 创建和静态方法。"""

    def test_colors_config(self) -> None:
        """验证所有类型都有颜色配置。"""
        for kind in ("info", "success", "warning", "error"):
            assert kind in _TOAST_COLORS
            assert "bg" in _TOAST_COLORS[kind]
            assert "fg" in _TOAST_COLORS[kind]
            assert "icon" in _TOAST_COLORS[kind]

    def test_info_icon(self) -> None:
        assert _TOAST_COLORS["info"]["icon"] == "ℹ"

    def test_success_icon(self) -> None:
        assert _TOAST_COLORS["success"]["icon"] == "✓"

    def test_warning_icon(self) -> None:
        assert _TOAST_COLORS["warning"]["icon"] == "⚠"

    def test_error_icon(self) -> None:
        assert _TOAST_COLORS["error"]["icon"] == "✗"

    def test_static_methods_exist(self) -> None:
        """验证静态便捷方法的存在。"""
        assert hasattr(Toast, "info")
        assert hasattr(Toast, "success")
        assert hasattr(Toast, "warning")
        assert hasattr(Toast, "error")