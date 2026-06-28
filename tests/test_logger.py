"""Logger / HistoryManager 单元测试。"""

import json
import os
import tempfile
from pathlib import Path

from core.logger import (
    HistoryEntry,
    HistoryManager,
    setup_logger,
    log_translation,
)


class TestHistoryEntry:
    """测试 HistoryEntry 序列化/反序列化。"""

    def test_to_dict(self) -> None:
        entry = HistoryEntry(
            source_text="hello",
            target_text="你好",
            source_lang="en",
            target_lang="zh",
            model="test-model",
            detected_lang="en",
            duration_ms=123.4,
            timestamp="2025-01-01T00:00:00",
            entry_id="test-id",
        )
        d = entry.to_dict()
        assert d["id"] == "test-id"
        assert d["source_text"] == "hello"
        assert d["target_text"] == "你好"
        assert d["duration_ms"] == 123.4

    def test_from_dict(self) -> None:
        d = {
            "id": "id-1",
            "timestamp": "2025-06-01T12:00:00",
            "source_text": "world",
            "target_text": "世界",
            "source_lang": "en",
            "target_lang": "zh",
            "model": "m",
            "detected_lang": "",
            "duration_ms": 50.0,
        }
        entry = HistoryEntry.from_dict(d)
        assert entry.source_text == "world"
        assert entry.target_text == "世界"
        assert entry.entry_id == "id-1"
        assert entry.duration_ms == 50.0

    def test_auto_timestamp(self) -> None:
        entry = HistoryEntry(
            source_text="a", target_text="b",
            source_lang="en", target_lang="zh",
            model="m",
        )
        assert entry.timestamp is not None
        assert entry.entry_id is not None


class TestHistoryManager:
    """测试 HistoryManager 的持久化和查询。"""

    def setup_method(self) -> None:
        self._tmp = tempfile.mktemp(suffix=".json")
        self._manager = HistoryManager(Path(self._tmp))
        # 填充测试数据，使用显式 ID 和时间戳确保顺序
        for i in range(5):
            self._manager.add_entry(
                HistoryEntry(
                    source_text=f"hello {i}",
                    target_text=f"你好 {i}",
                    source_lang="en",
                    target_lang="zh",
                    model="m",
                    timestamp=f"2025-06-28T10:00:0{i}",
                    entry_id=f"id-{i}",
                )
            )

    def teardown_method(self) -> None:
        if os.path.exists(self._tmp):
            os.remove(self._tmp)

    def test_add_and_count(self) -> None:
        assert self._manager.count() == 5

    def test_list_entries_recent_first(self) -> None:
        entries = self._manager.list_entries(limit=10)
        assert len(entries) == 5
        # 最新的在前
        assert entries[0].source_text == "hello 4"

    def test_list_entries_offset_limit(self) -> None:
        entries = self._manager.list_entries(limit=2, offset=1)
        assert len(entries) == 2
        assert entries[0].source_text == "hello 3"

    def test_clear(self) -> None:
        self._manager.clear()
        assert self._manager.count() == 0

    def test_remove_entry(self) -> None:
        entries = self._manager.list_entries(limit=10)
        eid = entries[0].entry_id
        assert self._manager.remove_entry(eid) is True
        assert self._manager.count() == 4

    def test_remove_entry_not_found(self) -> None:
        assert self._manager.remove_entry("nonexistent") is False

    def test_persistence(self) -> None:
        """验证数据写入文件后可重新加载。"""
        manager2 = HistoryManager(Path(self._tmp))
        assert manager2.count() == 5
        assert manager2.list_entries(limit=1)[0].source_text == "hello 4"

    def test_search(self) -> None:
        results = self._manager.search("hello")
        assert len(results) == 5

    def test_search_empty(self) -> None:
        results = self._manager.search("xyz")
        assert len(results) == 0

    def test_search_partial(self) -> None:
        results = self._manager.search("ello 3")
        assert len(results) == 1

    def test_max_entries(self) -> None:
        """超过最大条目数时自动裁剪。"""
        from core.logger import _HISTORY_MAX_ENTRIES
        for i in range(_HISTORY_MAX_ENTRIES + 100):
            self._manager.add_entry(
                HistoryEntry(
                    source_text=f"bulk {i}",
                    target_text="",
                    source_lang="en",
                    target_lang="zh",
                    model="m",
                )
            )
        assert self._manager.count() <= _HISTORY_MAX_ENTRIES

    def test_corrupted_file(self) -> None:
        """损坏的 JSON 文件启动为空列表。"""
        Path(self._tmp).write_text("{invalid json", encoding="utf-8")
        manager = HistoryManager(Path(self._tmp))
        assert manager.count() == 0

    def test_empty_file(self) -> None:
        """空文件启动为空列表。"""
        Path(self._tmp).write_text("", encoding="utf-8")
        manager = HistoryManager(Path(self._tmp))
        assert manager.count() == 0

    def test_no_file(self) -> None:
        """文件不存在启动为空列表。"""
        manager = HistoryManager(Path("/nonexistent/history.json"))
        assert manager.count() == 0