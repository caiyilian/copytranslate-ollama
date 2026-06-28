"""Pipeline 单元测试。"""

from core.pipeline import Pipeline


class TestPipeline:
    def test_translate_once(self) -> None:
        """测试单次翻译流程。"""
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

    def test_translate_once_with_cleaner(self) -> None:
        """测试含净化的单次翻译。"""
        p = Pipeline()
        try:
            # 带连字符断词的文本
            result = p.translate_once(
                "transla-\ntion is use-\nful",
                source="en",
                target="zh",
            )
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            p.close()

    def test_version_import(self) -> None:
        """验证 main.py 版本常量的可导入性。"""
        from main import VERSION, PROJECT
        assert VERSION == "0.1.0"
        assert PROJECT == "CopyTranslator-Ollama"
