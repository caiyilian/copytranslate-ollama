"""MainWindow 功能测试（无头模式）。"""

from core.pipeline import Pipeline


class TestMainWindow:
    def test_pipeline_integration(self) -> None:
        """验证 MainWindow 使用的 Pipeline 能正常工作。"""
        p = Pipeline()
        try:
            result = p.translate_once(
                "hello world",
                source="en",
                target="zh",
            )
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            p.close()

    def test_translate_non_english(self) -> None:
        """测试非英文翻译。"""
        p = Pipeline()
        try:
            result = p.translate_once(
                "bonjour",
                source="fr",
                target="zh",
                model="ali6parmak/hy-mt1.5:1.8b",
            )
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            p.close()
