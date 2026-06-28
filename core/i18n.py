"""国际化（i18n）模块。

支持多语言翻译，使用简单的字典映射。
默认语言为中文（zh-CN），可切换为英文（en）。
"""

from __future__ import annotations

import threading
from typing import Callable, Dict, Optional


# ---------------------------------------------------------------------------
# 翻译数据
# ---------------------------------------------------------------------------

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh-CN": {
        # 应用名
        "app_name": "CopyTranslator-Ollama",
        "app_desc": "基于 Ollama 的桌面翻译工具",

        # 菜单
        "menu_file": "文件",
        "menu_edit": "编辑",
        "menu_view": "视图",
        "menu_settings": "设置",
        "menu_help": "帮助",

        # 主界面
        "translate": "翻译",
        "clear": "清空",
        "focus_mode": "专注模式 >>",
        "contrast_mode": "<< 对照模式",
        "auto_translate": "自动翻译",
        "listening": "监听中",
        "paused": "已暂停",
        "translate_hint": "Ctrl+Enter",
        "source": "原文",
        "target": "译文",
        "model": "模型",
        "source_lang": "源语言",
        "target_lang": "目标语言",
        "listen": "剪贴板监听",
        "status_ready": "就绪",
        "status_empty": "请输入原文",
        "status_translating": "翻译中...",
        "status_error": "错误",
        "status_clear": "已清空",
        "status_saved": "设置已保存",
        "status_loaded": "已加载快照",
        "status_listen_on": "剪贴板监听已恢复",
        "status_listen_off": "剪贴板监听已暂停",
        "status_export": "已导出",

        # 快捷键
        "hotkey_toggle": "显示/隐藏窗口",
        "hotkey_model": "切换翻译模型",
        "hotkey_mode": "切换对照/专注模式",
        "hotkey_translate": "手动触发翻译",

        # 文件菜单
        "export": "导出",
        "import": "导入",
        "exit": "退出",

        # 视图菜单
        "history": "历史",
        "stats": "统计",
        "log": "日志",

        # 设置
        "settings": "设置",
        "general": "常规",
        "translation_tab": "翻译",
        "clipboard_tab": "剪贴板",
        "cleaner_tab": "净化",
        "output_tab": "输出",
        "hotkey_tab": "快捷键",
        "save": "保存",
        "cancel": "取消",
        "about": "关于",
        "language": "语言",
        "minimize_to_tray": "最小化到托盘",

        # 导出
        "export_title": "导出翻译",
        "export_range": "导出范围",
        "export_all": "全部",
        "export_50": "最近 50 条",
        "export_100": "最近 100 条",
        "export_format": "导出格式",
        "export_success": "已导出 {count} 条到:\n{path}",
        "save_file": "保存导出文件",
        "export_failed": "无法写入文件",

        # 关于
        "version": "版本",
        "author": "作者",
        "license": "许可证",
        "platform": "平台",
        "features": "功能特性",
        "github": "GitHub",

        # 错误
        "error": "错误",
        "warning": "警告",
        "info": "信息",
        "translation_failed": "翻译失败: {error}",
        "ollama_error": "Ollama 连接错误",
        "model_not_found": "模型未找到: {model}",

        # 确认
        "confirm": "确认",
        "confirm_clear": "确定清空所有日志？",
        "confirm_delete": "确定删除快照 '{name}' 吗？",
        "confirm_restore": "确定恢复快照 '{name}' 吗？",
        "yes": "是",
        "no": "否",
    },

    "en": {
        # Application
        "app_name": "CopyTranslator-Ollama",
        "app_desc": "Desktop translation tool based on Ollama",

        # Menu
        "menu_file": "File",
        "menu_edit": "Edit",
        "menu_view": "View",
        "menu_settings": "Settings",
        "menu_help": "Help",

        # Main UI
        "translate": "Translate",
        "clear": "Clear",
        "focus_mode": "Focus Mode >>",
        "contrast_mode": "<< Contrast Mode",
        "auto_translate": "Auto",
        "listening": "Listening",
        "paused": "Paused",
        "translate_hint": "Ctrl+Enter",
        "source": "Source",
        "target": "Target",
        "model": "Model",
        "source_lang": "From",
        "target_lang": "To",
        "listen": "Clipboard",
        "status_ready": "Ready",
        "status_empty": "Enter source text",
        "status_translating": "Translating...",
        "status_error": "Error",
        "status_clear": "Cleared",
        "status_saved": "Settings saved",
        "status_loaded": "Snapshot loaded",
        "status_listen_on": "Clipboard monitoring resumed",
        "status_listen_off": "Clipboard monitoring paused",
        "status_export": "Exported",

        # Shortcut
        "hotkey_toggle": "Toggle window visibility",
        "hotkey_model": "Switch translation model",
        "hotkey_mode": "Switch contrast/focus mode",
        "hotkey_translate": "Manual translate trigger",

        # File menu
        "export": "Export",
        "import": "Import",
        "exit": "Exit",

        # View menu
        "history": "History",
        "stats": "Stats",
        "log": "Log",

        # Settings
        "settings": "Settings",
        "general": "General",
        "translation_tab": "Translation",
        "clipboard_tab": "Clipboard",
        "cleaner_tab": "Cleaner",
        "output_tab": "Output",
        "hotkey_tab": "Hotkeys",
        "save": "Save",
        "cancel": "Cancel",
        "about": "About",
        "language": "Language",
        "minimize_to_tray": "Minimize to tray",

        # Export
        "export_title": "Export translations",
        "export_range": "Range",
        "export_all": "All",
        "export_50": "Last 50",
        "export_100": "Last 100",
        "export_format": "Format",
        "export_success": "Exported {count} entries to:\n{path}",
        "save_file": "Save exported file",
        "export_failed": "Cannot write file",

        # About
        "version": "Version",
        "author": "Author",
        "license": "License",
        "platform": "Platform",
        "features": "Features",
        "github": "GitHub",

        # Errors
        "error": "Error",
        "warning": "Warning",
        "info": "Info",
        "translation_failed": "Translation failed: {error}",
        "ollama_error": "Ollama connection error",
        "model_not_found": "Model not found: {model}",

        # Confirmation
        "confirm": "Confirm",
        "confirm_clear": "Clear all logs?",
        "confirm_delete": "Delete snapshot '{name}'?",
        "confirm_restore": "Restore snapshot '{name}'?",
        "yes": "Yes",
        "no": "No",
    },
}

# ---------------------------------------------------------------------------
# 全局状态
# ---------------------------------------------------------------------------

_locale_lock = threading.Lock()
_current_locale: str = "zh-CN"

# 观察者回调（语言变更时通知 UI 刷新）
_observers: list[Callable[[], None]] = []


def get_locale() -> str:
    """获取当前语言代码。"""
    return _current_locale


def set_locale(locale: str) -> None:
    """设置当前语言。

    Args:
        locale: 语言代码，如 "zh-CN" 或 "en"。
    """
    global _current_locale
    with _locale_lock:
        if locale in TRANSLATIONS:
            _current_locale = locale
            # 通知观察者
            for cb in _observers:
                try:
                    cb()
                except Exception:
                    pass


def register_observer(callback: Callable[[], None]) -> None:
    """注册语言变更观察者。"""
    _observers.append(callback)


def unregister_observer(callback: Callable[[], None]) -> None:
    """移除语言变更观察者。"""
    try:
        _observers.remove(callback)
    except ValueError:
        pass


def _(key: str) -> str:
    """翻译函数。

    Args:
        key: 翻译键名。

    Returns:
        当前语言的翻译文本，如果不存在返回键名本身。
    """
    with _locale_lock:
        lang_dict = TRANSLATIONS.get(_current_locale, TRANSLATIONS["zh-CN"])
        return lang_dict.get(key, key)


def _n(singular: str, plural: str, count: int) -> str:
    """复数翻译。

    Args:
        singular: 单数翻译键。
        plural: 复数翻译键。
        count: 数量。

    Returns:
        当前语言的翻译文本。
    """
    key = singular if count == 1 else plural
    return _(key)


def available_locales() -> list[str]:
    """返回可用的语言代码列表。"""
    return list(TRANSLATIONS.keys())


def locale_name(locale: str) -> str:
    """获取语言的本地显示名。"""
    names = {
        "zh-CN": "简体中文",
        "en": "English",
    }
    return names.get(locale, locale)