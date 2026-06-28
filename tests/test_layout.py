"""Layout 布局管理器单元测试。"""

from pathlib import Path

from core.layout import (
    delete_layout,
    get_default_layout,
    get_safe_layout,
    load_layout,
    save_layout,
)


class TestLayout:
    """测试布局管理器。"""

    def test_save_and_load(self) -> None:
        """保存后能正确加载。"""
        save_layout(x=200, y=300, width=800, height=600, mode="focus")
        data = load_layout()
        assert data is not None
        assert data["x"] == 200
        assert data["y"] == 300
        assert data["width"] == 800
        assert data["height"] == 600
        assert data["mode"] == "focus"

    def test_load_nonexistent(self) -> None:
        """文件不存在返回 None。"""
        delete_layout()
        assert load_layout() is None

    def test_default_layout(self) -> None:
        """默认布局包含所有必要字段。"""
        layout = get_default_layout()
        assert "x" in layout
        assert "y" in layout
        assert "width" in layout
        assert "height" in layout
        assert "mode" in layout
        assert "splitter_ratio" in layout

    def test_safe_layout_within_screen(self) -> None:
        """安全布局确保窗口在屏幕范围内。"""
        save_layout(x=99999, y=99999, width=99999, height=99999)
        safe = get_safe_layout(1920, 1080)
        assert safe["x"] + safe["width"] <= 1920
        assert safe["y"] + safe["height"] <= 1080

    def test_safe_layout_splitter_ratio(self) -> None:
        """分割器比例在有效范围内。"""
        save_layout(splitter_ratio=0.0)
        safe = get_safe_layout()
        assert safe["splitter_ratio"] >= 0.1

        save_layout(splitter_ratio=1.0)
        safe = get_safe_layout()
        assert safe["splitter_ratio"] <= 0.9

    def test_delete_layout(self) -> None:
        """删除布局文件。"""
        save_layout()
        assert delete_layout() is True
        assert load_layout() is None

    def test_extra_fields(self) -> None:
        """支持额外自定义字段。"""
        save_layout(custom_key="custom_value", another=123)
        data = load_layout()
        assert data is not None
        assert data["custom_key"] == "custom_value"
        assert data["another"] == 123

    def test_corrupted_file(self) -> None:
        """损坏的 JSON 文件返回 None。"""
        from core.layout import _LAYOUT_FILE
        _LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LAYOUT_FILE.write_text("{invalid", encoding="utf-8")
        assert load_layout() is None