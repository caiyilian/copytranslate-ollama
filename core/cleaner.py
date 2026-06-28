"""文本净化模块。

处理 PDF 复制产生的断行/断词问题，提供可组合的净化管道。
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# 不可见字符
# ---------------------------------------------------------------------------

# BOM (Byte Order Mark)
_BOM_CHARS = "\ufeff\ufffe"

# 零宽字符
_ZERO_WIDTH_CHARS = "\u200b\u200c\u200d\u2060\ufeff"

# Unicode 控制字符（保留 \n \r \t）
_CONTROL_CHARS = "".join(
    chr(c)
    for c in range(0x00, 0x20)
    if chr(c) not in "\n\r\t"
)

_INVISIBLE_PATTERN = re.compile(
    f"[{re.escape(_BOM_CHARS + _ZERO_WIDTH_CHARS + _CONTROL_CHARS)}]"
)


def remove_invisible_chars(text: str) -> str:
    """去除 BOM、零宽空格、控制字符（保留 \\n \\r \\t）。

    Args:
        text: 原始文本。

    Returns:
        净化后的文本。
    """
    return _INVISIBLE_PATTERN.sub("", text)


# ---------------------------------------------------------------------------
# 连字符断词修复
# ---------------------------------------------------------------------------

# 连字符断词模式：单词 + 连字符 + 换行 + 单词续
_HYPHENATION_PATTERN = re.compile(r"(\w)-\s*\n\s*(\w)")


def fix_hyphenation(text: str) -> str:
    """修复 PDF 中的连字符断词。

    将 "transla-\\ntion" 修复为 "translation"。

    Args:
        text: 含连字符断词的文本。

    Returns:
        修复后的文本。
    """
    return _HYPHENATION_PATTERN.sub(r"\1\2", text)


# ---------------------------------------------------------------------------
# 句子结束标点
# ---------------------------------------------------------------------------

_SENTENCE_ENDERS = ".!?。！？…"


def _line_ends_sentence(line: str) -> bool:
    """判断行末是否为句子结束标点。"""
    stripped = line.rstrip()
    if not stripped:
        return False
    return stripped[-1] in _SENTENCE_ENDERS


def _line_starts_newline_before(text: str) -> bool:
    """判断行首是否为英文大写字母开头（可能为句首）。"""
    stripped = text.lstrip()
    if not stripped:
        return False
    return stripped[0].isupper()


def _is_bullet_or_numbered_line(line: str) -> bool:
    """判断是否为列表项（bullet / 编号行）。"""
    stripped = line.strip()
    if not stripped:
        return False
    # 匹配 bullet 符号
    if re.match(r"^[\u2022\u2023\u25E6\u2043\u2219*\-•·]\s", stripped):
        return True
    # 匹配编号 (1. / (1) / 1) / a. / i. 等)
    if re.match(r"^[\(]?\d+[\.\)]\s", stripped):
        return True
    if re.match(r"^[\(]?[a-zA-Z][\.\)]\s", stripped):
        return True
    return False


def merge_lines(
    text: str,
    sentence_enders: Optional[str] = None,
) -> str:
    """合并段落内被换行断开的行。

    - 行末有句号/问号/感叹号 → 保留换行（潜在段落分界）
    - 行末无句号且下一行非大写开头 → 合并（同一句子）
    - 列表项（bullet / 编号） → 保留独立

    Args:
        text: 输入文本。
        sentence_enders: 句子结束标点集合，默认 .!?。！？…

    Returns:
        合并后的文本。
    """
    if not text:
        return text

    enders = sentence_enders or _SENTENCE_ENDERS
    lines = text.split("\n")
    result: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 空行 → 段落分隔，保留
        if not line.strip():
            result.append(line)
            i += 1
            continue

        # 列表项 → 保留独立
        if _is_bullet_or_numbered_line(line):
            result.append(line)
            i += 1
            continue

        # 查找后续非空行
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1

        if j >= len(lines):
            # 最后一行
            result.append(line)
            break

        next_line = lines[j]

        # 判断是否应该合并
        line_ends = line.rstrip()
        ends_with_ender = (
            line_ends and line_ends[-1] in enders
        )

        # 行末是句号或下一行是列表项 → 不合并
        if ends_with_ender or _is_bullet_or_numbered_line(next_line):
            result.append(line)
            i += 1
            continue

        # 下一行是小写/数字开头 → 合并
        if (
            next_line.lstrip()
            and not next_line.lstrip()[0].isupper()
        ):
            # 合并 i 和 j 行
            merged = line.rstrip() + " " + next_line.lstrip()
            # 替换 lines 中的 i 行
            lines[i] = merged
            lines.pop(j)
            continue

        # 默认不合并
        result.append(line)
        i += 1

    return "\n".join(result)


# ---------------------------------------------------------------------------
# 组合管道
# ---------------------------------------------------------------------------


class TextCleaner:
    """文本净化管道。

    按顺序执行多个净化步骤，每步可独立开关。

    用法:
        cleaner = TextCleaner()
        result = cleaner.clean("transla-\\ntion")
    """

    def __init__(
        self,
        fix_hyphenation: bool = True,
        merge_paragraph_lines: bool = True,
        preserve_paragraph_breaks: bool = True,
    ) -> None:
        self._steps: List[Tuple[str, bool]] = [
            ("remove_invisible", True),
            ("fix_hyphenation", fix_hyphenation),
            ("merge_lines", merge_paragraph_lines),
        ]

    def clean(self, text: str) -> str:
        """执行完整净化管道。"""
        result = text

        for step_name, enabled in self._steps:
            if not enabled:
                continue

            if step_name == "remove_invisible":
                result = remove_invisible_chars(result)
            elif step_name == "fix_hyphenation":
                result = fix_hyphenation(result)
            elif step_name == "merge_lines":
                result = merge_lines(result)

        return result
