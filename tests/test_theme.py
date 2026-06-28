"""Theme 主题管理器单元测试。"""

from core.theme import (
    available_themes,
    get_color,
    get_colors,
    get_effective_theme,
    get_theme,
    set_theme,
    theme_display_name,
    toggle_theme,
)


class TestTheme:
    """测试主题管理器。"""

    def test_default_theme(self) -> None:
        """默认主题是 system。"""
        assert get_theme() == "system"

    def test_set_light_theme(self) -> None:
        set_theme("light")
        assert get_theme() == "light"

    def test_set_dark_theme(self) -> None:
        set_theme("dark")
        assert get_theme() == "dark"

    def test_set_invalid_theme(self) -> None:
        """设置无效主题不改变当前值。"""
        set_theme("invalid")
        assert get_theme() in ("light", "dark", "system")

    def test_toggle_theme(self) -> None:
        """切换主题。"""
        set_theme("light")
        result = toggle_theme()
        assert result == "dark"
        result = toggle_theme()
        assert result == "light"

    def test_get_effective_theme(self) -> None:
        """获取实际生效主题。"""
        set_theme("light")
        assert get_effective_theme() == "light"
        set_theme("dark")
        assert get_effective_theme() == "dark"

    def test_get_colors(self) -> None:
        """获取主题颜色。"""
        colors = get_colors("light")
        assert "bg" in colors
        assert "fg" in colors
        assert "accent" in colors

    def test_get_color(self) -> None:
        """获取指定颜色。"""
        color = get_color("bg", "light")
        assert color.startswith("#")

    def test_available_themes(self) -> None:
        """可用主题列表。"""
        themes = available_themes()
        assert "light" in themes
        assert "dark" in themes
        assert "system" in themes

    def test_theme_display_name(self) -> None:
        """主题显示名。"""
        assert theme_display_name("light") in ("浅色", "Light")
        assert theme_display_name("dark") in ("深色", "Dark")

    def test_light_dark_differ(self) -> None:
        """浅色和深色主题颜色不同。"""
        light_bg = get_color("bg", "light")
        dark_bg = get_color("bg", "dark")
        assert light_bg != dark_bg