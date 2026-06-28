"""日志与翻译历史记录模块。

提供两级日志：
1. 文件日志 — 记录程序运行中的各类事件（翻译、错误、配置变更）
2. 翻译历史 — 记录每次翻译的原文/译文/元数据，保存在 JSON 文件中
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 文件系统路径
# ---------------------------------------------------------------------------

_DATA_DIR = Path.home() / ".copytranslate-ollama"
_LOG_FILE = _DATA_DIR / "app.log"
_HISTORY_FILE = _DATA_DIR / "history.json"

# ---------------------------------------------------------------------------
# 文件日志
# ---------------------------------------------------------------------------

_FILE_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_FILE_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str = "copytranslate",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """配置并返回命名日志器。

    Args:
        name: 日志器名称。
        level: 日志级别。
        log_file: 日志文件路径，默认 ~/.copytranslate-ollama/app.log。

    Returns:
        配置好的 Logger 实例。
    """
    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除已有 handler，避免重复添加
    logger.handlers.clear()

    # 文件 handler
    fh = logging.FileHandler(
        str(log_file or _LOG_FILE),
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter(_FILE_LOG_FORMAT, _FILE_LOG_DATE_FORMAT))
    logger.addHandler(fh)

    # 控制台 handler（stderr）
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    return logger


# 默认应用日志器
app_logger = setup_logger()


def log_translation(
    source_text: str,
    target_text: str,
    source_lang: str,
    target_lang: str,
    model: str,
    duration_ms: float,
) -> None:
    """记录翻译事件到文件日志。"""
    app_logger.info(
        "TRANSLATE model=%s %s->%s len=%d chars=%d %.1fms",
        model,
        source_lang,
        target_lang,
        len(source_text),
        len(target_text),
        duration_ms,
    )


# ---------------------------------------------------------------------------
# 翻译历史
# ---------------------------------------------------------------------------

_HISTORY_MAX_ENTRIES = 500


class HistoryEntry:
    """单条翻译历史记录。"""

    def __init__(
        self,
        source_text: str,
        target_text: str,
        source_lang: str,
        target_lang: str,
        model: str,
        detected_lang: str = "",
        duration_ms: float = 0.0,
        timestamp: Optional[str] = None,
        entry_id: Optional[str] = None,
    ) -> None:
        self.source_text = source_text
        self.target_text = target_text
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.model = model
        self.detected_lang = detected_lang
        self.duration_ms = duration_ms
        self.timestamp = timestamp or datetime.now().isoformat()
        self.entry_id = entry_id or self.timestamp

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。"""
        return {
            "id": self.entry_id,
            "timestamp": self.timestamp,
            "source_text": self.source_text,
            "target_text": self.target_text,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "model": self.model,
            "detected_lang": self.detected_lang,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        """从字典反序列化。"""
        return cls(
            source_text=data.get("source_text", ""),
            target_text=data.get("target_text", ""),
            source_lang=data.get("source_lang", ""),
            target_lang=data.get("target_lang", ""),
            model=data.get("model", ""),
            detected_lang=data.get("detected_lang", ""),
            duration_ms=data.get("duration_ms", 0.0),
            timestamp=data.get("timestamp"),
            entry_id=data.get("id"),
        )


class HistoryManager:
    """翻译历史管理器，基于 JSON 文件持久化。"""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self._file = file_path or _HISTORY_FILE
        self._entries: List[HistoryEntry] = []
        self._load()

    # ------------------------------------------------------------------
    # 内部 I/O
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """从文件加载历史记录。"""
        if not self._file.exists():
            self._entries = []
            return
        try:
            raw = self._file.read_text(encoding="utf-8")
            data: List[Dict[str, Any]] = json.loads(raw)
            self._entries = [HistoryEntry.from_dict(d) for d in data]
        except (json.JSONDecodeError, OSError):
            self._entries = []

    def _save(self) -> None:
        """保存历史记录到文件。"""
        self._file.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._entries]
        self._file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_entries(
        self, limit: int = 100, offset: int = 0
    ) -> List[HistoryEntry]:
        """获取历史条目，按时间倒序（最新在前）。"""
        sorted_entries = sorted(
            self._entries, key=lambda e: e.timestamp, reverse=True
        )
        return sorted_entries[offset : offset + limit]

    def count(self) -> int:
        """返回总条目数。"""
        return len(self._entries)

    # ------------------------------------------------------------------
    # 修改
    # ------------------------------------------------------------------

    def add_entry(self, entry: HistoryEntry) -> None:
        """添加一条翻译历史记录。"""
        self._entries.append(entry)
        # 限制最大条目数
        if len(self._entries) > _HISTORY_MAX_ENTRIES:
            self._entries = self._entries[-_HISTORY_MAX_ENTRIES:]
        self._save()

    def clear(self) -> None:
        """清空所有历史记录。"""
        self._entries.clear()
        self._save()

    def remove_entry(self, entry_id: str) -> bool:
        """按 ID 删除单条记录。"""
        before = len(self._entries)
        self._entries = [e for e in self._entries if e.entry_id != entry_id]
        if len(self._entries) < before:
            self._save()
            return True
        return False

    # ------------------------------------------------------------------
    # 搜索
    # ------------------------------------------------------------------

    def search(self, keyword: str, limit: int = 50) -> List[HistoryEntry]:
        """搜索原文或译文包含关键字的条目。"""
        kw = keyword.lower()
        results = []
        for entry in reversed(self._entries):
            if kw in entry.source_text.lower() or kw in entry.target_text.lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        return results