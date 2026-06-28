"""快捷键编辑器。

解析和格式化快捷键组合，验证是否合法，检测冲突。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

# 修饰键
_MODIFIERS = {"Control", "Alt", "Shift", "Win"}

# 常用键
_COMMON_KEYS = {
    "A": "A", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F",
    "G": "G", "H": "H", "I": "I", "J": "J", "K": "K", "L": "L",
    "M": "M", "N": "N", "O": "O", "P": "P", "Q": "Q", "R": "R",
    "S": "S", "T": "T", "U": "U", "V": "V", "W": "W", "X": "X",
    "Y": "Y", "Z": "Z",
    "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
    "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
    "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4", "F5": "F5",
    "F6": "F6", "F7": "F7", "F8": "F8", "F9": "F9", "F10": "F10",
    "F11": "F11", "F12": "F12",
    "Enter": "Enter", "Return": "Return",
    "Tab": "Tab", "Space": "Space",
    "Escape": "Esc", "Esc": "Esc",
    "Delete": "Delete", "BackSpace": "Backspace",
    "Home": "Home", "End": "End",
    "PageUp": "PgUp", "PageDown": "PgDown",
    "Insert": "Insert",
    "Left": "←", "Right": "→", "Up": "↑", "Down": "↓",
}


def parse_hotkey(hotkey_str: str) -> Optional[Tuple[str, ...]]:
    """解析快捷键字符串为键元组。

    Args:
        hotkey_str: 如 "Ctrl+Shift+T"

    Returns:
        解析后的键元组，如 ("Control", "Shift", "T")。
        无效格式返回 None。
    """
    if not hotkey_str or not hotkey_str.strip():
        return None

    parts = [p.strip() for p in hotkey_str.split("+")]
    if len(parts) < 2:
        return None  # 至少需要修饰键+一个键

    modifiers = []
    main_key = None

    for part in parts:
        part_lower = part.lower()
        if part_lower in ("control", "ctrl"):
            if "Control" in modifiers:
                return None
            modifiers.append("Control")
        elif part_lower in ("alt",):
            if "Alt" in modifiers:
                return None
            modifiers.append("Alt")
        elif part_lower in ("shift",):
            if "Shift" in modifiers:
                return None
            modifiers.append("Shift")
        elif part_lower in ("win", "super", "meta"):
            if "Win" in modifiers:
                return None
            modifiers.append("Win")
        else:
            if main_key is not None:
                return None  # 多个主键，无效
            # 查找标准名称
            key_found = None
            for std_name, canonical in _COMMON_KEYS.items():
                if std_name.lower() == part_lower or canonical.lower() == part_lower:
                    key_found = canonical
                    break
            if key_found is None:
                # 尝试直接使用（如特殊字符）
                if len(part) == 1:
                    key_found = part.upper()
                else:
                    return None
            main_key = key_found

    if main_key is None:
        return None

    # 按标准顺序排序修饰键
    order = {"Control": 0, "Alt": 1, "Shift": 2, "Win": 3}
    modifiers.sort(key=lambda x: order.get(x, 99))

    return tuple(modifiers + [main_key])


def format_hotkey(parts: Tuple[str, ...]) -> str:
    """格式化键元组为显示字符串。

    Args:
        parts: 如 ("Control", "Shift", "T")

    Returns:
        显示字符串，如 "Ctrl+Shift+T"
    """
    if not parts:
        return ""

    display_map = {
        "Control": "Ctrl",
        "Alt": "Alt",
        "Shift": "Shift",
        "Win": "Win",
    }

    main_key = parts[-1]
    modifiers = [display_map.get(p, p) for p in parts[:-1]]
    return "+".join(modifiers + [main_key])


def validate_hotkey(
    hotkey_str: str,
    existing_hotkeys: Optional[List[str]] = None,
) -> Tuple[bool, str]:
    """验证快捷键字符串是否有效且无冲突。

    Args:
        hotkey_str: 要验证的字符串
        existing_hotkeys: 已存在的快捷键列表

    Returns:
        Tuple[str, str]: (是否有效, 错误消息)
    """
    parsed = parse_hotkey(hotkey_str)
    if parsed is None:
        return False, "快捷键格式无效"

    if not existing_hotkeys:
        return True, ""

    current_formatted = format_hotkey(parsed)
    for existing in existing_hotkeys:
        existing_parsed = parse_hotkey(existing)
        if existing_parsed and format_hotkey(existing_parsed) == current_formatted:
            return False, f"与已有快捷键冲突: {existing}"

    return True, ""


def is_valid_hotkey(hotkey_str: str) -> bool:
    """简单判断快捷键格式是否有效。"""
    return parse_hotkey(hotkey_str) is not None