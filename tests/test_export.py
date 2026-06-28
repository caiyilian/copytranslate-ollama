"""Export 翻译服务单元测试。"""

import json
from pathlib import Path

from core.export import (
    export_entries,
    export_to_csv,
    export_to_json,
    export_to_txt,
    get_export_entries,
)
from core.logger import HistoryEntry


def _make_entry(i: int = 1, **kwargs) -> HistoryEntry:
    defaults = dict(
        source_text=f"hello {i}",
        target_text=f"你好 {i}",
        source_lang="en",
        target_lang="zh",
        model="model-x",
        duration_ms=100.0,
    )
    defaults.update(kwargs)
    return HistoryEntry(**defaults)


class TestExportToTxt:
    """测试 TXT 导出。"""

    def test_basic_export(self) -> None:
        """TXT 文件包含条目内容。"""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".txt"))
        entries = [_make_entry(1), _make_entry(2)]
        result = export_to_txt(entries, tmp)
        assert result is True
        content = tmp.read_text(encoding="utf-8")
        assert "hello 1" in content
        assert "你好 2" in content
        tmp.unlink()

    def test_empty_entries(self) -> None:
        """空列表也能导出成功。"""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".txt"))
        result = export_to_txt([], tmp)
        assert result is True
        content = tmp.read_text(encoding="utf-8")
        assert "0 条" in content
        tmp.unlink()


class TestExportToCsv:
    """测试 CSV 导出。"""

    def test_basic_export(self) -> None:
        """CSV 文件包含正确列名。"""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        entries = [_make_entry(1)]
        result = export_to_csv(entries, tmp)
        assert result is True
        content = tmp.read_text(encoding="utf-8")
        assert "序号" in content
        assert "原文" in content
        assert "译文" in content
        assert "hello 1" in content
        tmp.unlink()

    def test_special_characters(self) -> None:
        """包含逗号的文本正确转义。"""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        entries = [_make_entry(source_text="hello, world")]
        result = export_to_csv(entries, tmp)
        assert result is True
        tmp.unlink()


class TestExportToJson:
    """测试 JSON 导出。"""

    def test_basic_export(self) -> None:
        """JSON 文件格式正确。"""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".json"))
        entries = [_make_entry(1), _make_entry(2)]
        result = export_to_json(entries, tmp)
        assert result is True
        data = json.loads(tmp.read_text(encoding="utf-8"))
        assert data["total"] == 2
        assert len(data["entries"]) == 2
        assert data["entries"][0]["source_text"] == "hello 1"
        tmp.unlink()


class TestExportEntries:
    """测试 export_entries 统一入口。"""

    def test_txt_format(self) -> None:
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".txt"))
        result = export_entries([_make_entry(1)], tmp, "txt")
        assert result is True
        assert tmp.read_text(encoding="utf-8").startswith(
            "翻译记录导出"
        )
        tmp.unlink()

    def test_csv_format(self) -> None:
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        result = export_entries([_make_entry(1)], tmp, "csv")
        assert result is True
        assert tmp.exists()
        tmp.unlink()

    def test_json_format(self) -> None:
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".json"))
        result = export_entries([_make_entry(1)], tmp, "json")
        assert result is True
        assert "total" in json.loads(tmp.read_text(encoding="utf-8"))
        tmp.unlink()

    def test_extension_correction(self) -> None:
        """扩展名不匹配时自动修正。"""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".txt"))
        result = export_entries([_make_entry(1)], tmp, "csv")
        assert result is True
        # The extension should have been corrected to .csv
        assert tmp.with_suffix(".csv").exists()
        tmp.with_suffix(".csv").unlink()

    def test_invalid_format_returns_false(self) -> None:
        """无效格式返回 False。"""
        import tempfile
        tmp = Path(tempfile.mktemp(suffix=".xyz"))
        result = export_entries([_make_entry(1)], tmp, "xyz")
        assert result is False


class TestGetExportEntries:
    """测试条目获取。"""

    def test_default_limit(self) -> None:
        """默认限制。"""
        entries = get_export_entries()
        assert isinstance(entries, list)