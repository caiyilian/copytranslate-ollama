"""日志查看后端服务。

解析应用日志文件，支持按关键字搜索和按级别过滤。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


# 日志行正则：2025-06-28 10:00:00 [LEVEL] name: message
_LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"\[(\w+)\]\s+"
    r"(.+?):\s+"
    r"(.*)$"
)


@dataclass
class LogEntry:
    """单条日志记录。"""
    timestamp: datetime
    level: str
    logger_name: str
    message: str
    raw_line: str


def parse_log_line(line: str) -> Optional[LogEntry]:
    """解析单行日志。"""
    m = _LOG_PATTERN.match(line.strip())
    if not m:
        return None
    ts_str, level, name, message = m.groups()
    try:
        ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return LogEntry(
        timestamp=ts,
        level=level,
        logger_name=name,
        message=message,
        raw_line=line.rstrip("\n"),
    )


def read_logs(
    file_path: Optional[Path] = None,
    level_filter: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[LogEntry]:
    """读取并过滤日志。

    Args:
        file_path: 日志文件路径，默认 ~/.copytranslate-ollama/app.log。
        level_filter: 过滤级别，如 "INFO"、"WARNING"、"ERROR"。
        keyword: 大小写不敏感关键字搜索。
        limit: 最多返回条数。
        offset: 跳过前 N 条。

    Returns:
        解析后的 LogEntry 列表（最新在前）。
    """
    if file_path is None:
        file_path = Path.home() / ".copytranslate-ollama" / "app.log"
    if not file_path.exists():
        return []

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    # 逆序（最新在前）
    lines = list(reversed(lines))

    entries: List[LogEntry] = []
    for line in lines:
        entry = parse_log_line(line)
        if entry is None:
            continue
        if level_filter and entry.level != level_filter:
            continue
        if keyword:
            kw = keyword.lower()
            if kw not in entry.message.lower() and kw not in entry.raw_line.lower():
                continue
        entries.append(entry)

    # 分页
    return entries[offset : offset + limit]


def count_logs(
    file_path: Optional[Path] = None,
    level_filter: Optional[str] = None,
    keyword: Optional[str] = None,
) -> int:
    """统计符合条件的日志条数。"""
    if file_path is None:
        file_path = Path.home() / ".copytranslate-ollama" / "app.log"
    if not file_path.exists():
        return 0

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return 0

    count = 0
    for line in lines:
        entry = parse_log_line(line)
        if entry is None:
            continue
        if level_filter and entry.level != level_filter:
            continue
        if keyword:
            kw = keyword.lower()
            if kw not in entry.message.lower() and kw not in entry.raw_line.lower():
                continue
        count += 1
    return count


def get_file_size(file_path: Optional[Path] = None) -> int:
    """返回日志文件大小（字节）。"""
    if file_path is None:
        file_path = Path.home() / ".copytranslate-ollama" / "app.log"
    if not file_path.exists():
        return 0
    return file_path.stat().st_size


def clear_logs(file_path: Optional[Path] = None) -> bool:
    """清空日志文件。"""
    if file_path is None:
        file_path = Path.home() / ".copytranslate-ollama" / "app.log"
    if not file_path.exists():
        return True
    try:
        file_path.write_text("", encoding="utf-8")
        return True
    except OSError:
        return False