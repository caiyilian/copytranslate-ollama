"""翻译统计服务。

从 HistoryManager 的历史数据中计算各类统计数据：
翻译总数、字符数、各模型使用量、各语言方向频次等。
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional

from core.logger import HistoryManager


class TranslationStats:
    """翻译统计数据。"""

    def __init__(
        self,
        total_translations: int = 0,
        total_source_chars: int = 0,
        total_target_chars: int = 0,
        model_counts: Optional[Dict[str, int]] = None,
        source_lang_counts: Optional[Dict[str, int]] = None,
        target_lang_counts: Optional[Dict[str, int]] = None,
        total_duration_ms: float = 0.0,
    ) -> None:
        self.total_translations = total_translations
        self.total_source_chars = total_source_chars
        self.total_target_chars = total_target_chars
        self.model_counts = model_counts or {}
        self.source_lang_counts = source_lang_counts or {}
        self.target_lang_counts = target_lang_counts or {}
        self.total_duration_ms = total_duration_ms

    @property
    def avg_duration_ms(self) -> float:
        """平均每次翻译耗时（毫秒）。"""
        if self.total_translations == 0:
            return 0.0
        return self.total_duration_ms / self.total_translations

    @property
    def top_model(self) -> str:
        """最常用的模型。"""
        if not self.model_counts:
            return "N/A"
        return max(self.model_counts, key=self.model_counts.get)

    @property
    def top_source_lang(self) -> str:
        """最常见的源语言。"""
        if not self.source_lang_counts:
            return "N/A"
        return max(self.source_lang_counts, key=self.source_lang_counts.get)

    @property
    def top_target_lang(self) -> str:
        """最常见的目标语言。"""
        if not self.target_lang_counts:
            return "N/A"
        return max(self.target_lang_counts, key=self.target_lang_counts.get)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。"""
        return {
            "total_translations": self.total_translations,
            "total_source_chars": self.total_source_chars,
            "total_target_chars": self.total_target_chars,
            "model_counts": dict(self.model_counts),
            "source_lang_counts": dict(self.source_lang_counts),
            "target_lang_counts": dict(self.target_lang_counts),
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "top_model": self.top_model,
            "top_source_lang": self.top_source_lang,
            "top_target_lang": self.top_target_lang,
        }


def compute_stats(
    history_manager: Optional[HistoryManager] = None,
) -> TranslationStats:
    """从历史管理器计算统计数据。

    Args:
        history_manager: 历史管理器实例，默认创建新实例。

    Returns:
        TranslationStats 对象。
    """
    hm = history_manager or HistoryManager()
    entries = hm.list_entries(limit=10000)  # 最多处理 10000 条

    total_source = 0
    total_target = 0
    total_duration = 0.0
    model_counter: Counter = Counter()
    source_lang_counter: Counter = Counter()
    target_lang_counter: Counter = Counter()

    for entry in entries:
        total_source += len(entry.source_text)
        total_target += len(entry.target_text)
        total_duration += entry.duration_ms
        if entry.model:
            model_counter[entry.model] += 1
        if entry.source_lang:
            source_lang_counter[entry.source_lang] += 1
        if entry.target_lang:
            target_lang_counter[entry.target_lang] += 1

    return TranslationStats(
        total_translations=len(entries),
        total_source_chars=total_source,
        total_target_chars=total_target,
        model_counts=dict(model_counter),
        source_lang_counts=dict(source_lang_counter),
        target_lang_counts=dict(target_lang_counter),
        total_duration_ms=total_duration,
    )