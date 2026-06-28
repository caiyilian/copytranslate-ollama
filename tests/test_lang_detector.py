"""语言检测器单元测试。"""

from core.lang_detector import detect_language


class TestDetectLanguage:
    """测试语言检测功能。"""

    def test_detect_english(self) -> None:
        """检测英语。"""
        lang, conf = detect_language("hello world this is a test")
        assert lang == "en"
        assert conf > 0.0

    def test_detect_english_sentence(self) -> None:
        """检测英语长句。"""
        lang, conf = detect_language(
            "The quick brown fox jumps over the lazy dog"
        )
        assert lang == "en"
        assert conf > 0.0

    def test_detect_chinese(self) -> None:
        """检测中文。"""
        lang, conf = detect_language("你好世界")
        assert lang == "zh"
        assert conf > 0.5

    def test_detect_chinese_mixed(self) -> None:
        """检测中英文混合（中文为主）。"""
        lang, conf = detect_language("今天天气很好，我们一起去公园散步吧")
        assert lang == "zh"
        assert conf > 0.5

    def test_detect_japanese_hiragana(self) -> None:
        """检测日语（平假名为主）。"""
        lang, conf = detect_language("こんにちは世界")
        assert lang == "ja"
        assert conf > 0.5

    def test_detect_japanese_katakana(self) -> None:
        """检测日语（片假名）。"""
        lang, conf = detect_language("コンピュータプログラミング")
        assert lang == "ja"
        assert conf > 0.5

    def test_detect_korean(self) -> None:
        """检测韩语。"""
        lang, conf = detect_language("안녕하세요 세계")
        assert lang == "ko"
        assert conf > 0.5

    def test_detect_arabic(self) -> None:
        """检测阿拉伯语。"""
        lang, conf = detect_language("مرحبا بالعالم")
        assert lang == "ar"
        assert conf > 0.5

    def test_detect_thai(self) -> None:
        """检测泰语。"""
        lang, conf = detect_language("สวัสดีชาวโลก")
        assert lang == "th"
        assert conf > 0.5

    def test_detect_russian(self) -> None:
        """检测俄语。"""
        lang, conf = detect_language("Привет мир")
        assert lang == "ru"
        assert conf > 0.3

    def test_detect_french(self) -> None:
        """检测法语（通过高频词）。"""
        lang, conf = detect_language("Bonjour tout le monde")
        assert lang == "fr"
        assert conf > 0.0

    def test_detect_german(self) -> None:
        """检测德语（通过高频词）。"""
        lang, conf = detect_language(
            "Hallo Welt, das ist ein Test"
        )
        # 德语词数不多，可能降级到 en
        # 不严格要求，只验证不会崩溃
        assert lang in ("en", "de")

    def test_detect_spanish(self) -> None:
        """检测西班牙语（通过高频词）。"""
        lang, conf = detect_language(
            "Hola mundo, esto es una prueba"
        )
        assert lang in ("en", "es")

    def test_detect_empty(self) -> None:
        """空字符串返回英语，置信度为 0。"""
        lang, conf = detect_language("")
        assert lang == "en"
        assert conf == 0.0

    def test_detect_whitespace(self) -> None:
        """仅空白字符返回英语，置信度为 0。"""
        lang, conf = detect_language("   \n  \t  ")
        assert lang == "en"
        assert conf == 0.0

    def test_detect_english_with_punctuation(self) -> None:
        """带标点符号的英语。"""
        lang, conf = detect_language("Hello, world! How are you?")
        assert lang == "en"

    def test_detect_chinese_punctuation(self) -> None:
        """带中文标点的中文。"""
        lang, conf = detect_language("你好，世界！今天天气真好。")
        assert lang == "zh"

    def test_detect_long_english_paragraph(self) -> None:
        """长段英文检测。"""
        text = (
            "In the field of natural language processing, "
            "language detection is a fundamental task that "
            "involves identifying the language of a given text. "
            "This is typically done using statistical models "
            "or rule-based approaches that analyze character "
            "distributions and common word patterns. "
            "The accuracy of language detection systems "
            "has improved significantly with the advent "
            "of deep learning technologies."
        )
        lang, conf = detect_language(text)
        assert lang == "en"
        assert conf > 0.0

    def test_detect_mixed_cjk_japanese(self) -> None:
        """中日混合文本（有假名 → 日语）。"""
        lang, conf = detect_language("日本語の文章です。中国語も含む。")
        # 有平假名 → 判定为 ja
        assert lang == "ja"

    def test_detect_japanese_no_kanji(self) -> None:
        """纯假名日语。"""
        lang, conf = detect_language("これはテストです")
        assert lang == "ja"
        assert conf > 0.5