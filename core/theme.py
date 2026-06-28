"""主题管理器。

支持浅色/深色/系统主题，持久化用户选择，通知 UI 刷新。
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Callable, Dict, Optional

# 配置文件路径
_CONFIG_FILE = Path.home() / ".copytranslate-ollama" / "ui.json"

# 全局状态
_lock = threading.Lock()
_current_theme: str = "system"  # "light" / "dark" / "system"
_observers: list[Callable[[], None]] = []


# ---------------------------------------------------------------------------
# 主题色板定义
# ---------------------------------------------------------------------------

THEME_COLORS: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#ffffff",
        "fg": "#000000",
        "bg_secondary": "#f5f5f5",
        "fg_secondary": "#555555",
        "accent": "#1976d2",
        "accent_fg": "#ffffff",
        "border": "#d0d0d0",
        "button_bg": "#e8e8e8",
        "button_fg": "#000000",
        "button_hover": "#d0d0d0",
        "entry_bg": "#ffffff",
        "entry_fg": "#000000",
        "entry_border": "#c0c0c0",
        "menu_bg": "#f5f5f5",
        "menu_fg": "#000000",
        "text_bg": "#ffffff",
        "text_fg": "#000000",
        "text_select_bg": "#1976d2",
        "text_select_fg": "#ffffff",
        "error": "#d32f2f",
        "warning": "#ed6c02",
        "success": "#2e7d32",
        "info": "#1976d2",
        "tooltip_bg": "#fffde7",
        "tooltip_fg": "#000000",
        "scrollbar_bg": "#e0e0e0",
        "scrollbar_fg": "#bdbdbd",
        "tray_bg": "#ffffff",
        "tray_fg": "#000000",
    },
    "dark": {
        "bg": "#1e1e1e",
        "fg": "#e0e0e0",
        "bg_secondary": "#2d2d2d",
        "fg_secondary": "#aaaaaa",
        "accent": "#64b5f6",
        "accent_fg": "#000000",
        "border": "#424242",
        "button_bg": "#333333",
        "button_fg": "#e0e0e0",
        "button_hover": "#444444",
        "entry_bg": "#2d2d2d",
        "entry_fg": "#e0e0e0",
        "entry_border": "#555555",
        "menu_bg": "#2d2d2d",
        "menu_fg": "#e0e0e0",
        "text_bg": "#1e1e1e",
        "text_fg": "#e0e0e0",
        "text_select_bg": "#64b5f6",
        "text_select_fg": "#000000",
        "error": "#ef5350",
        "warning": "#ff9800",
        "success": "#66bb6a",
        "info": "#64b5f6",
        "tooltip_bg": "#333333",
        "tooltip_fg": "#e0e0e0",
        "scrollbar_bg": "#424242",
        "scrollbar_fg": "#757575",
        "tray_bg": "#2d2d2d",
        "tray_fg": "#e0e0e0",
    },
}


# ---------------------------------------------------------------------------
# 核心 API
# ---------------------------------------------------------------------------

def get_theme() -> str:
    """获取当前主题名（light / dark / system）。"""
    with _lock:
        return _current_theme


def get_effective_theme() -> str:
    """获取实际生效的主题（解析 system）。"""
    theme = get_theme()
    if theme == "system":
        return _detect_system_theme()
    return theme


def set_theme(theme: str) -> None:
    """设置主题。

    Args:
        theme: "light" / "dark" / "system"
    """
    global _current_theme
    with _lock:
        if theme in ("light", "dark", "system"):
            _current_theme = theme
            _save_theme()
            for cb in _observers:
                try:
                    cb()
                except Exception:
                    pass


def toggle_theme() -> str:
    """切换主题：light -> dark -> light。

    Returns:
        切换后的主题名。
    """
    current = get_effective_theme()
    if current == "dark":
        set_theme("light")
        return "light"
    else:
        set_theme("dark")
        return "dark"


def get_colors(theme: Optional[str] = None) -> Dict[str, str]:
    """获取指定主题的颜色字典。

    Args:
        theme: 主题名，默认使用当前实际生效主题。

    Returns:
        颜色名 -> 颜色值 的字典。
    """
    name = theme or get_effective_theme()
    return THEME_COLORS.get(name, THEME_COLORS["light"])


def get_color(name: str, theme: Optional[str] = None) -> str:
    """获取指定颜色。

    Args:
        name: 颜色名（如 "bg", "fg", "accent"）。
        theme: 主题名，默认使用当前实际生效主题。

    Returns:
        颜色值（如 "#ffffff"）。
    """
    colors = get_colors(theme)
    return colors.get(name, "#000000")


def register_observer(callback: Callable[[], None]) -> None:
    """注册主题变更观察者。"""
    _observers.append(callback)


def unregister_observer(callback: Callable[[], None]) -> None:
    """移除主题变更观察者。"""
    try:
        _observers.remove(callback)
    except ValueError:
        pass


def available_themes() -> list[str]:
    """返回可用主题列表。"""
    return ["light", "dark", "system"]


def theme_display_name(theme: str) -> str:
    """获取主题的显示名。"""
    names = {
        "light": "浅色",
        "dark": "深色",
        "system": "跟随系统",
    }
    return names.get(theme, theme)


# ---------------------------------------------------------------------------
# 系统主题检测
# ---------------------------------------------------------------------------

def _detect_system_theme() -> str:
    """检测系统主题。"""
    try:
        if os.name == "nt":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return "light" if value else "dark"
    except Exception:
        pass

    # 默认浅色
    return "light"


# ---------------------------------------------------------------------------
# 持久化
# ---------------------------------------------------------------------------

def _save_theme() -> None:
    """保存主题到配置文件。"""
    try:
        data: Dict[str, str] = {}
        if _CONFIG_FILE.exists():
            try:
                data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                data = {}
        data["theme"] = _current_theme
        _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def load_theme() -> None:
    """从配置文件加载主题。"""
    global _current_theme
    if _CONFIG_FILE.exists():
        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            theme = data.get("theme", "system")
            if theme in ("light", "dark", "system"):
                _current_theme = theme
        except (json.JSONDecodeError, OSError):
            pass


# 启动时加载
load_theme()