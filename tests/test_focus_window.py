"""FocusWindow 功能测试（无头模式）。"""

from core.pipeline import Pipeline


class TestFocusWindow:
    def test_pipeline_translate(self) -> None:
        """验证 FocusWindow 使用的 Pipeline 能正常工作。"""
        p = Pipeline()
        try:
            result, detected = p.translate_once("hello", source="en", target="zh")
            assert isinstance(result, str)
            assert isinstance(detected, str)
            assert len(result) > 0
        finally:
            p.close()

    def test_focus_import(self) -> None:
        """验证 FocusWindow 模块可导入。"""
        from ui.focus_window import FocusWindow
        assert FocusWindow is not None
