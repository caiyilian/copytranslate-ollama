"""i18n 国际化模块单元测试。"""

from core.i18n import (
    _,
    available_locales,
    get_locale,
    locale_name,
    register_observer,
    set_locale,
    unregister_observer,
)


class TestI18n:
    """测试国际化模块。"""

    def test_default_locale(self) -> None:
        """默认语言是中文。"""
        assert get_locale() == "zh-CN"

    def test_set_locale(self) -> None:
        """可以设置语言。"""
        set_locale("en")
        assert get_locale() == "en"
        # 恢复
        set_locale("zh-CN")

    def test_set_invalid_locale(self) -> None:
        """设置无效语言不改变当前语言。"""
        set_locale("invalid_locale")
        assert get_locale() == "zh-CN"

    def test_translate_existing_key(self) -> None:
        """翻译存在的键。"""
        set_locale("en")
        assert _("translate") == "Translate"
        set_locale("zh-CN")
        assert _("translate") == "翻译"

    def test_translate_missing_key(self) -> None:
        """翻译不存在的键返回键名。"""
        assert _("nonexistent_key") == "nonexistent_key"

    def test_available_locales(self) -> None:
        """可用语言列表包含中英文。"""
        locales = available_locales()
        assert "zh-CN" in locales
        assert "en" in locales

    def test_locale_name(self) -> None:
        """获取语言显示名。"""
        assert "中文" in locale_name("zh-CN") or "简体" in locale_name("zh-CN")
        assert locale_name("en") == "English"

    def test_observer(self) -> None:
        """语言变更通知观察者。"""
        called = []

        def observer():
            called.append(True)

        register_observer(observer)
        set_locale("en")
        assert len(called) == 1
        set_locale("zh-CN")
        assert len(called) == 2
        unregister_observer(observer)

    def test_unregister_observer(self) -> None:
        """移除观察者。"""
        def observer():
            pass

        register_observer(observer)
        unregister_observer(observer)

    def test_observer_exception(self) -> None:
        """观察者异常不影响语言切换。"""
        def bad_observer():
            raise RuntimeError("test")

        register_observer(bad_observer)
        # 不应抛出
        set_locale("en")
        set_locale("zh-CN")
        unregister_observer(bad_observer)