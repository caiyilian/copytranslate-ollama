"""Translator 单元测试。"""

from core.translator import clean_response, build_prompt, _resolve_lang_name


class TestResolveLangName:
    def test_known_code(self) -> None:
        assert _resolve_lang_name("en") == "English"
        assert _resolve_lang_name("zh") == "Chinese"
        assert _resolve_lang_name("ja") == "Japanese"

    def test_unknown_code(self) -> None:
        assert _resolve_lang_name("xx") == "xx"


class TestBuildPrompt:
    def test_translategemma_template(self) -> None:
        prompt = build_prompt(
            "hello", "en", "zh", model="translategemma:4b"
        )
        assert "English" in prompt
        assert "Chinese" in prompt
        assert "hello" in prompt
        assert "<bos>" in prompt
        assert "professional" in prompt

    def test_standard_template(self) -> None:
        prompt = build_prompt(
            "bonjour",
            "fr",
            "zh",
            model="ali6parmak/hy-mt1.5:1.8b",
        )
        assert "French" in prompt
        assert "Chinese" in prompt
        assert "bonjour" in prompt
        assert "Translate the following" in prompt
        # 标准模板不含 <bos> 和专业说明
        assert "<bos>" not in prompt


class TestCleanResponse:
    def test_no_prefix(self) -> None:
        assert clean_response("你好世界") == "你好世界"

    def test_remove_sure_prefix(self) -> None:
        assert (
            clean_response("Sure, here is the translation: 你好")
            == "你好"
        )

    def test_remove_here_prefix(self) -> None:
        assert (
            clean_response("Here is the translation: 你好世界")
            == "你好世界"
        )

    def test_remove_quotes(self) -> None:
        assert clean_response('"你好世界"') == "你好世界"

    def test_whitespace_only(self) -> None:
        assert clean_response("  ") == ""

    def test_translate_prefix(self) -> None:
        assert (
            clean_response("Translation: 你好")
            == "你好"
        )

    def test_strip_whitespace(self) -> None:
        assert clean_response("  你好世界  ") == "你好世界"
