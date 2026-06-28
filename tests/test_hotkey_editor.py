"""Hotkey Editor 快捷键编辑器单元测试。"""

import pytest

from core.hotkey_editor import (
    format_hotkey,
    is_valid_hotkey,
    parse_hotkey,
    validate_hotkey,
)


class TestParseHotkey:
    """测试快捷键解析。"""

    def test_valid_ctrl_shift_t(self) -> None:
        result = parse_hotkey("Ctrl+Shift+T")
        assert result is not None
        assert "Control" in result
        assert "Shift" in result
        assert "T" in result

    def test_valid_alt_f1(self) -> None:
        result = parse_hotkey("Alt+F1")
        assert result is not None
        assert "Alt" in result
        assert "F1" in result

    def test_valid_single_modifier_key(self) -> None:
        result = parse_hotkey("Ctrl+Return")
        assert result is not None
        assert len(result) >= 2

    def test_invalid_no_modifier(self) -> None:
        """无修饰键无效。"""
        assert parse_hotkey("T") is None

    def test_invalid_empty(self) -> None:
        assert parse_hotkey("") is None
        assert parse_hotkey("   ") is None

    def test_invalid_duplicate_modifier(self) -> None:
        assert parse_hotkey("Ctrl+Ctrl+T") is None

    def test_invalid_no_key(self) -> None:
        assert parse_hotkey("Ctrl+Shift") is None

    def test_modifier_order_normalized(self) -> None:
        """修饰键应按标准顺序排列。"""
        result = parse_hotkey("Shift+Ctrl+T")
        assert result is not None
        assert result[0] == "Control"
        assert result[1] == "Shift"

    def test_case_insensitive_modifiers(self) -> None:
        result = parse_hotkey("ctrl+shift+t")
        assert result is not None

    def test_control_alias(self) -> None:
        result = parse_hotkey("Control+Shift+T")
        assert result is not None

    def test_return_alias(self) -> None:
        result = parse_hotkey("Ctrl+Return")
        assert result is not None
        assert "Return" in result


class TestFormatHotkey:
    """测试快捷键格式化。"""

    def test_format_modifiers(self) -> None:
        assert format_hotkey(("Control", "Shift", "T")) == "Ctrl+Shift+T"

    def test_format_single_modifier(self) -> None:
        assert format_hotkey(("Alt", "F1")) == "Alt+F1"

    def test_format_empty(self) -> None:
        assert format_hotkey(()) == ""


class TestValidateHotkey:
    """测试快捷键验证。"""

    def test_valid_no_conflict(self) -> None:
        valid, error = validate_hotkey("Ctrl+Shift+T", [])
        assert valid is True
        assert error == ""

    def test_conflict_detected(self) -> None:
        valid, error = validate_hotkey("Ctrl+Shift+T", ["Ctrl+Shift+T"])
        assert valid is False
        assert "冲突" in error

    def test_invalid_format(self) -> None:
        valid, error = validate_hotkey("Ctrl+Shift", ["Alt+F1"])
        assert valid is False
        assert "格式" in error

    def test_no_false_positive_conflict(self) -> None:
        """不同快捷键不冲突。"""
        valid, _ = validate_hotkey("Ctrl+Shift+W", ["Ctrl+Shift+T"])
        assert valid is True


class TestIsValidHotkey:
    """测试快速验证函数。"""

    def test_valid_cases(self) -> None:
        assert is_valid_hotkey("Ctrl+Shift+T") is True
        assert is_valid_hotkey("Ctrl+Return") is True
        assert is_valid_hotkey("Ctrl+Shift+F") is True
        assert is_valid_hotkey("Alt+V") is True
        assert is_valid_hotkey("Shift+O") is True

    def test_invalid_cases(self) -> None:
        assert is_valid_hotkey("") is False
        assert is_valid_hotkey("T") is False
        assert is_valid_hotkey("Ctrl+Shift") is False
        assert is_valid_hotkey("InvalidKey") is False