"""Stats 统计服务单元测试。"""

from core.logger import HistoryEntry
from core.logger import HistoryManager
from core.stats import TranslationStats, compute_stats


class TestTranslationStats:
    """测试 TranslationStats 数据类和属性。"""

    def test_empty_stats(self) -> None:
        """空统计应有默认值。"""
        stats = TranslationStats()
        assert stats.total_translations == 0
        assert stats.total_source_chars == 0
        assert stats.total_target_chars == 0
        assert stats.avg_duration_ms == 0.0
        assert stats.top_model == "N/A"
        assert stats.top_source_lang == "N/A"
        assert stats.top_target_lang == "N/A"

    def test_avg_duration(self) -> None:
        """平均耗时计算正确。"""
        stats = TranslationStats(
            total_translations=10,
            total_duration_ms=5000.0,
        )
        assert stats.avg_duration_ms == 500.0

    def test_top_model(self) -> None:
        """最常用模型。"""
        stats = TranslationStats(
            model_counts={"model-a": 10, "model-b": 5}
        )
        assert stats.top_model == "model-a"

    def test_top_model_empty(self) -> None:
        stats = TranslationStats()
        assert stats.top_model == "N/A"

    def test_top_source_lang(self) -> None:
        stats = TranslationStats(
            source_lang_counts={"en": 20, "zh": 5}
        )
        assert stats.top_source_lang == "en"

    def test_top_target_lang(self) -> None:
        stats = TranslationStats(
            target_lang_counts={"zh": 20, "de": 3}
        )
        assert stats.top_target_lang == "zh"

    def test_to_dict(self) -> None:
        """序列化包含所有字段。"""
        stats = TranslationStats(
            total_translations=5,
            total_source_chars=100,
            total_target_chars=80,
            model_counts={"m1": 3, "m2": 2},
            source_lang_counts={"en": 5},
            target_lang_counts={"zh": 5},
            total_duration_ms=2500.0,
        )
        d = stats.to_dict()
        assert d["total_translations"] == 5
        assert d["top_model"] == "m1"
        assert d["avg_duration_ms"] == 500.0


class TestComputeStats:
    """测试 compute_stats 函数。"""

    def test_empty_history(self) -> None:
        """空历史返回零值统计。"""
        hm = _make_history([])
        stats = compute_stats(hm)
        assert stats.total_translations == 0

    def test_single_entry(self) -> None:
        """单条记录。"""
        hm = _make_history([
            HistoryEntry("hello", "你好", "en", "zh", "model-x"),
        ])
        stats = compute_stats(hm)
        assert stats.total_translations == 1
        assert stats.total_source_chars == 5
        assert stats.total_target_chars == 2
        assert stats.model_counts["model-x"] == 1
        assert stats.source_lang_counts["en"] == 1
        assert stats.target_lang_counts["zh"] == 1

    def test_multiple_entries(self) -> None:
        """多条记录累计统计。"""
        hm = _make_history([
            HistoryEntry("hello", "你好", "en", "zh", "m1"),
            HistoryEntry("world", "世界", "en", "zh", "m1"),
            HistoryEntry("bonjour", "你好", "fr", "zh", "m2"),
        ])
        stats = compute_stats(hm)
        assert stats.total_translations == 3
        assert stats.total_source_chars == 5 + 5 + 7  # 17
        assert stats.total_target_chars == 2 + 2 + 2  # 6
        assert stats.model_counts["m1"] == 2
        assert stats.model_counts["m2"] == 1
        assert stats.source_lang_counts["en"] == 2
        assert stats.source_lang_counts["fr"] == 1
        assert stats.top_model == "m1"
        assert stats.top_source_lang == "en"


def _make_history(entries):
    """Helper: 用指定条目创建 HistoryManager。"""
    import tempfile
    from pathlib import Path

    tmp = tempfile.mktemp(suffix=".json")
    hm = HistoryManager(Path(tmp))
    for e in entries:
        hm.add_entry(e)
    return hm